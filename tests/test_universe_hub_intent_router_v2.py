"""Rule-based hub ask routing — no LLM."""



from __future__ import annotations



from pathlib import Path

from urllib.parse import quote





def _router_path() -> Path:

    return (

        Path(__file__).resolve().parents[1]

        / "projects"

        / "no1kmedi"

        / "src"

        / "lib"

        / "universeHubIntentRouterV2.ts"

    )





def test_intent_router_module_exists():

    assert _router_path().is_file()





def _validate(question: str, intent: str | None) -> bool:

    q = question.strip()

    return bool(q or intent)





def resolve(question: str, intent: str | None) -> str | None:

    """Mirror resolveHubAskRoute contract without executing TS."""

    if not _validate(question, intent):

        return None



    q = question.strip()

    dev_hints = ["api", "압축", "개발"]

    obs_hints = ["관측", "오라클"]

    customize_hints = ["b2b", "페르소나", "가드"]

    reports_hints = ["리포트", "보고서"]

    clinician_hints = ["한의사", "진료", "clinician"]



    chosen = intent

    if chosen is None and q:

        lower = q.lower()

        if any(h in lower or h in q for h in dev_hints):

            chosen = "developer"

        elif any(h in q for h in obs_hints):

            chosen = "observe"

        elif any(h in lower or h in q for h in customize_hints):

            chosen = "customize"

        elif any(h in lower or h in q for h in reports_hints):

            chosen = "reports"

        elif any(h in lower or h in q for h in clinician_hints):

            chosen = "clinician"

        else:

            chosen = "life"

    if chosen is None:

        chosen = "life"



    hub = "source=jema_hub_v2"

    if chosen == "observe":

        return f"/hub/oracle?prefill={q}&{hub}" if q else "/hub/oracle"

    if chosen == "developer":

        return f"/hub/developer?prefill={q}&{hub}" if q else "/hub/developer"

    if chosen == "customize":

        return f"/hub/customize?prefill={q}&{hub}" if q else "/hub/customize"

    if chosen == "reports":

        return f"/hub/reports?prefill={q}&{hub}" if q else "/hub/reports"

    if chosen == "clinician":

        return f"/clinician?prefill={q}&{hub}" if q else "/clinician"



    base = "https://mkmlife.com/ask-one"

    if not q:

        return f"{base}?{hub}"

    return f"{base}?prefill={quote(q)}&{hub}"





def test_empty_submit_blocked():

    assert resolve("", None) is None





def test_intent_chip_without_question_allowed():

    assert resolve("", "observe") == "/hub/oracle"

    assert resolve("", "customize") == "/hub/customize"

    assert resolve("", "clinician") == "/clinician"





def test_keyword_inference_routes():

    assert "/hub/oracle" in resolve("시장 관측", None)

    assert "/hub/developer" in resolve("압축 API", None)

    assert "/hub/customize" in resolve("B2B 가드", None)

    assert "/hub/reports" in resolve("내 리포트", None)

    assert resolve("한의사 문진", None).startswith("/clinician")





def test_life_prefill_external():

    assert "prefill=hello" in resolve("hello", "life")


