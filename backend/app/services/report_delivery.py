

import logging
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.models.entities import ReportRecipient
from app.services.email import EmailError, send_mail, smtp_configured
from app.services.reports import daily_report

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


class ReportDeliveryError(Exception):
    def __init__(self, *, status_code: int, detail: str, code: str) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code


def today_in_app_tz() -> date:
    return datetime.now(ZoneInfo(get_settings().app_timezone)).date()


def list_recipients(session: Session, user_id: int) -> list[ReportRecipient]:
    return list(
        session.execute(
            select(ReportRecipient)
            .where(ReportRecipient.user_id == user_id)
            .order_by(ReportRecipient.id)
        ).scalars()
    )


def add_recipient(session: Session, user_id: int, email: str) -> ReportRecipient:
    cleaned = email.strip().lower()
    if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
        raise ReportDeliveryError(
            status_code=422, detail="邮箱格式不对", code="invalid_email"
        )
    existing = session.execute(
        select(ReportRecipient).where(
            ReportRecipient.user_id == user_id,
            ReportRecipient.email == cleaned,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    recipient = ReportRecipient(user_id=user_id, email=cleaned)
    session.add(recipient)
    session.commit()
    session.refresh(recipient)
    return recipient


def delete_recipient(session: Session, user_id: int, recipient_id: int) -> None:
    recipient = session.get(ReportRecipient, recipient_id)
    if recipient is None or recipient.user_id != user_id:
        raise ReportDeliveryError(
            status_code=404, detail="收件邮箱不存在", code="recipient_not_found"
        )
    session.delete(recipient)
    session.commit()


def send_daily(session: Session, user_id: int, day: date | None = None) -> dict:
    report_day = day or today_in_app_tz()
    recipients = [r for r in list_recipients(session, user_id) if r.enabled]
    if not recipients:
        raise ReportDeliveryError(
            status_code=422, detail="还没有配置收件邮箱", code="no_recipient"
        )
    if not smtp_configured():
        raise ReportDeliveryError(
            status_code=503, detail="邮件发送尚未配置（缺 SMTP 授权码）", code="smtp_unconfigured"
        )
    subject, text_body, html_body = build_daily_mail(session, user_id, report_day)
    sent: list[str] = []
    try:
        for recipient in recipients:
            send_mail(recipient.email, subject, text_body, html_body)
            sent.append(recipient.email)
    except EmailError as exc:
        raise ReportDeliveryError(
            status_code=exc.status_code, detail=exc.detail, code=exc.code
        ) from exc
    return {"sent": len(sent), "recipients": sent, "date": report_day}


def build_daily_mail(session: Session, user_id: int, day: date) -> tuple[str, str, str]:
    report = daily_report(session, user_id, day)
    subject = f"【糖安食助】{day} 每日饮食报告"
    return subject, _text_body(report), _html_body(report)


def _text_body(report: dict) -> str:
    lines = [f"您好，以下是 {report['date']} 的每日饮食记录：", ""]
    lines.append("【今日饮食】")
    if report["meal_count"] == 0:
        lines.append("今天还没有加入饮食计划。")
    else:
        for item in report["items"]:
            lines.append(f"- {item['meal_type']} {item['name']}（{_show(item['kcal'])} kcal）")
    lines.append("")
    lines.append("【小结】")
    lines.extend(_summary_lines(report))
    lines.append("")
    lines.append("以上数据来自计划内食谱，仅供参考，不构成医疗建议。")
    return "\n".join(lines)


def _summary_lines(report: dict) -> list[str]:
    lines: list[str] = []
    totals = report["totals"]
    kcal = totals["kcal"]
    target = report["kcal_target"]
    if report["meal_count"] == 0:
        lines.append("今天还没有加入饮食计划，可以先去「今日推荐」看看。")
    elif kcal is None:
        lines.append("有食谱缺热量，今日热量暂无法合计。")
    elif target is None:
        lines.append(f"今日热量 {_show(kcal)} kcal（尚未设置每日目标）。")
    elif kcal > target:
        lines.append(f"今日热量 {_show(kcal)} kcal，超出每日目标 {target} kcal。")
    elif kcal < target:
        lines.append(f"今日热量 {_show(kcal)} kcal，低于每日目标 {target} kcal。")
    else:
        lines.append(f"今日热量 {_show(kcal)} kcal，正好达到每日目标。")
    ratios = report["energy_ratios"]
    if ratios["carb"] is not None:
        lines.append(
            f"供能比：碳水 {_show(ratios['carb'])}%、蛋白质 {_show(ratios['protein'])}%、脂肪 {_show(ratios['fat'])}%。"
        )
    fiber = totals["fiber_g"]
    if fiber is not None:
        lines.append(f"膳食纤维 {_show(fiber)} 克。")
    return lines or ["暂无可总结的数据。"]


def _html_body(report: dict) -> str:
    if report["meal_count"] == 0:
        items_html = "<li>今天还没有加入饮食计划。</li>"
    else:
        items_html = "".join(
            f"<li>{item['meal_type']} {item['name']}（{_show(item['kcal'])} kcal）</li>"
            for item in report["items"]
        )
    summary_html = "".join(f"<li>{line}</li>" for line in _summary_lines(report))
    return (
        "<div style='font-family:sans-serif;max-width:560px;margin:auto;color:#2b3a31;'>"
        f"<h2>每日饮食报告</h2><p>您好，以下是 {report['date']} 的每日饮食记录：</p>"
        f"<h3>今日饮食</h3><ul>{items_html}</ul>"
        f"<h3>小结</h3><ul>{summary_html}</ul>"
        "<p style='color:#8a9a90;font-size:12px;'>以上数据来自计划内食谱，仅供参考，不构成医疗建议。</p>"
        "</div>"
    )


def _show(value) -> str:
    if value is None:
        return "—"
    text = format(float(value), ".1f")
    return text.rstrip("0").rstrip(".")


def run_daily_delivery() -> int:
    """定时任务：给所有启用收件邮箱发送当日报告。"""
    if not smtp_configured():
        logger.warning("每日报告未发送：SMTP 未配置")
        return 0
    sent_count = 0
    try:
        factory = get_sessionmaker()
        with factory() as session:
            recipients = list(
                session.execute(
                    select(ReportRecipient).where(ReportRecipient.enabled.is_(True))
                ).scalars()
            )
            by_user: dict[int, list[str]] = {}
            for recipient in recipients:
                by_user.setdefault(recipient.user_id, []).append(recipient.email)
            report_day = today_in_app_tz()
            for user_id, emails in by_user.items():
                try:
                    subject, text_body, html_body = build_daily_mail(
                        session, user_id, report_day
                    )
                    for email in emails:
                        send_mail(email, subject, text_body, html_body)
                        sent_count += 1
                except Exception:  # noqa: BLE001
                    logger.exception("发送给 user %s 失败", user_id)
    except Exception:  # noqa: BLE001
        logger.exception("每日报告定时发送失败")
    return sent_count


def start_report_scheduler() -> None:
    global _scheduler
    if _scheduler is not None or os.environ.get("PYTEST_CURRENT_TEST"):
        return
    settings = get_settings()
    scheduler = BackgroundScheduler(timezone=settings.app_timezone)
    scheduler.add_job(
        run_daily_delivery,
        trigger="cron",
        hour=settings.report_send_hour,
        minute=settings.report_send_minute,
        id="report-delivery",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler


def stop_report_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
