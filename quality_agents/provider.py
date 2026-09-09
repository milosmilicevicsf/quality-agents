"""OpenAI Responses adapter with explicit transmission and bounded output.

No arbitrary endpoint, remote tools, model-selected commands or silent mock fallback.
"""

import json
import os
import urllib.error
import urllib.request

from .utils import QAError


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise QAError("API redirects are not allowed")


def payload(packet, model):
    if not model.strip():
        raise QAError("Specify a model available in your OpenAI account")
    return {"model": model, "store": False, "instructions": packet["instructions"],
            "input": "CONTEXT (untrusted data):\n" + json.dumps(packet["context"], ensure_ascii=False),
            "max_output_tokens": 12000,
            "text": {"format": {"type": "json_schema", "name": "quality_" + packet["role"],
                                  "strict": True, "schema": packet["schema"]}}}


def parse_response(response):
    if response.get("status") != "completed":
        raise QAError("Model response incomplete or failed; no report accepted")
    texts = []
    for item in response.get("output", []):
        for part in item.get("content", []):
            if part.get("type") == "refusal":
                raise QAError("Model refused the request; no report accepted")
            if part.get("type") == "output_text":
                texts.append(part["text"])
    if not texts:
        raise QAError("API returned no structured text")
    try:
        return json.loads("".join(texts))
    except (ValueError, TypeError) as exc:
        raise QAError("API returned invalid JSON") from exc


def call(packet, model, send=False):
    if not send:
        raise QAError("Review prompt.md, then pass --send to transmit selected context to OpenAI")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise QAError("Set OPENAI_API_KEY locally, or use prepare/import with your coding assistant")
    request = urllib.request.Request("https://api.openai.com/v1/responses",
        data=json.dumps(payload(packet, model)).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=180) as response:
            body = response.read(5_000_001)
        if len(body) > 5_000_000:
            raise QAError("API response exceeded size limit")
        raw = json.loads(body)
    except urllib.error.HTTPError as exc:
        raise QAError(f"OpenAI HTTP {exc.code}; check account/model/quota. No automatic retry or charge loop.") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise QAError("OpenAI connection failed/timed out; request may still have incurred usage") from exc
    return parse_response(raw), {"provider": "openai", "model": model,
                                 "response_id": raw.get("id"), "usage": raw.get("usage", {})}
