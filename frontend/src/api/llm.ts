import http from "./http";

export interface LlmConfigView {
  provider: string;
  model: string;
  base_url: string;
  api_key_masked: string;
  configured: boolean;
  status: string;
}

export interface LlmConfigPayload {
  provider: string;
  api_key: string;
  model: string;
  base_url: string;
}

export interface LlmTestResult {
  ok: boolean;
  message: string;
}

export function fetchLlmConfig() {
  return http.get<LlmConfigView>("/api/v1/llm-config");
}

export function saveLlmConfig(payload: LlmConfigPayload) {
  return http.put<LlmConfigView>("/api/v1/llm-config", payload);
}

export function testLlmConfig(payload: LlmConfigPayload) {
  // 测试连接会真的请求模型服务，超时放宽到 30 秒
  return http.post<LlmTestResult>("/api/v1/llm-config/test", payload, {
    timeout: 30000,
  });
}
