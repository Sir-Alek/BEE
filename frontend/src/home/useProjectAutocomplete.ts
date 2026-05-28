import { useEffect, useState } from "react";
import { readProjectFile } from "../api";
import {
  buildProjectAutocompleteContext,
  EMPTY_AUTOCOMPLETE_CONTEXT,
  ProjectAutocompleteContext,
} from "./editorAutocomplete";

export function useProjectAutocomplete(
  platform: string,
  project: string,
  files: { path: string }[],
  refreshKey = 0,
): ProjectAutocompleteContext {
  const fileKey = files.map((f) => f.path).join("\n");
  const [context, setContext] = useState<ProjectAutocompleteContext>(EMPTY_AUTOCOMPLETE_CONTEXT);

  useEffect(() => {
    if (!project.trim() || files.length === 0) {
      setContext(EMPTY_AUTOCOMPLETE_CONTEXT);
      return;
    }

    let cancelled = false;
    void buildProjectAutocompleteContext(files, (path) => readProjectFile(platform, project, path).then((r) => r.content))
      .then((ctx) => {
        if (!cancelled) setContext(ctx);
      })
      .catch(() => {
        if (!cancelled) setContext(EMPTY_AUTOCOMPLETE_CONTEXT);
      });

    return () => {
      cancelled = true;
    };
  }, [platform, project, fileKey, refreshKey]);

  return context;
}
