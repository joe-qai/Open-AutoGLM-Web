"""Debug: capture exactly what the API returns (headers + body)."""
import httpx

url = 'https://test-info-ai-gateway-api.lockin.com/v1/chat/completions'
payload = {
    "model": "glm-5.1",
    "messages": [{"role": "user", "content": "Respond with exactly: OK"}],
    "max_tokens": 10,
}
headers = {
    "Authorization": "Bearer sk-no3vq...",
    "Content-Type": "application/json",
}

with httpx.Client(timeout=15) as client:
    resp = client.post(url, json=payload, headers=headers)
    print(f'Status: {resp.status_code}')
    print(f'Content-Type: {resp.headers.get("content-type")}')
    body = resp.text
    print(f'Body (first 1000): {body[:1000]}')
