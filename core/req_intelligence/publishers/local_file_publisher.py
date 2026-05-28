"""Guardado local opt-in de .feature (descarga / output dir)."""
from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, Dict

from core.req_intelligence.publishers.base import PublishContext, PublishResult


class LocalFilePublisher:
    target = "local_file"

    def publish(self, ctx: PublishContext) -> PublishResult:
        out_dir = (ctx.output_dir or "").strip()
        if not out_dir:
            from core.elia_paths import doc_features_dir

            out_dir = str(doc_features_dir())
        os.makedirs(out_dir, exist_ok=True)
        slug = re.sub(r"[^\w\-]+", "_", ctx.feature_name or "feature").strip("_") or "feature"
        if ctx.file_path.strip():
            name = os.path.basename(ctx.file_path.replace("\\", "/"))
        else:
            name = f"{slug}.feature"
        if not name.lower().endswith(".feature"):
            name += ".feature"
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(ctx.gherkin_text)
        return PublishResult(True, "local_file", f"Guardado en {path}", external_id=name, url=path)

    def smoke_test(self, profile: Dict[str, Any]) -> PublishResult:
        del profile
        return PublishResult(True, "local_file", "Salida local disponible")
