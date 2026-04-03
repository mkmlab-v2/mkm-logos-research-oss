# JSON Schema + stdio MCP (Python, L2 reference)

**목적:** L2에서 말하는 **타입세이프 MCP**를 **외부 상표 없이** 재현하는 최소 표본이다.  
입력은 MCP `Tool.input_schema`와 동일한 JSON Schema로 **런타임 `jsonschema` 검증**까지 이중 적용한다.

## 도구

| 이름 | 입력 | 동작 |
|------|------|------|
| `sentiment_ratio` | `{ "ratio": number }` — 반드시 **0.0~1.0** | 검증 후 JSON 한 줄 텍스트 반환 (스텁) |

## 실행

```powershell
cd C:\workspace\experiments\mcp-jsonschema-stdio
py -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python server.py
```

글로벌 `py`에 `mcp`가 이미 있으면 `py server.py`만으로도 동작할 수 있다(권장: 위 venv).

MCP Inspector 등으로 stdio 연결해 도구 목록·호출을 확인한다.

## 경계

- **본선·실매매·`projects/bitcoin-trading/ops` 자동 합선 금지.**
- `ministack.org` MiniStack(AWS 에뮬)과 **무관**.
- Copilot SDK 실험은 `../copilot-sdk-mcp/README.md` 참고.

## SSOT

- L2 마일스톤·도구 경계: `docs/final/P0_COMMERCIALIZATION_TRACKER.md`
