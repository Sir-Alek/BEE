import { Completion, CompletionContext, CompletionResult } from "@codemirror/autocomplete";

export type StepDefinition = {
  keyword: "given" | "when" | "then" | "step";
  text: string;
  source: string;
};

export type ProjectAutocompleteContext = {
  steps: StepDefinition[];
  pageMethods: Record<string, string[]>;
  scenarioNames: string[];
  featureNames: string[];
  jsonKeys: string[];
  buttonFunctions: string[];
};

export const EMPTY_AUTOCOMPLETE_CONTEXT: ProjectAutocompleteContext = {
  steps: [],
  pageMethods: {},
  scenarioNames: [],
  featureNames: [],
  jsonKeys: [],
  buttonFunctions: [],
};

const STEP_DECORATOR_RE = /@(given|when|then|step)\(\s*(['"])((?:\\.|(?!\2).)*)\2/gi;
const PY_METHOD_RE = /^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(/gm;
const FEATURE_NAME_RE = /^\s*Feature:\s*(.+)\s*$/gim;
const SCENARIO_NAME_RE = /^\s*Scenario(?: Outline)?:\s*(.+)\s*$/gim;

const GHERKIN_KEYWORDS = [
  { label: "Feature:", type: "keyword" as const, detail: "Gherkin" },
  { label: "Scenario:", type: "keyword" as const, detail: "Gherkin" },
  { label: "Scenario Outline:", type: "keyword" as const, detail: "Gherkin" },
  { label: "Background:", type: "keyword" as const, detail: "Gherkin" },
  { label: "Given ", type: "keyword" as const, detail: "Gherkin" },
  { label: "When ", type: "keyword" as const, detail: "Gherkin" },
  { label: "Then ", type: "keyword" as const, detail: "Gherkin" },
  { label: "And ", type: "keyword" as const, detail: "Gherkin" },
  { label: "But ", type: "keyword" as const, detail: "Gherkin" },
];

const STEP_DECORATORS = [
  { label: "@given('", type: "keyword" as const, detail: "Behave step" },
  { label: "@when('", type: "keyword" as const, detail: "Behave step" },
  { label: "@then('", type: "keyword" as const, detail: "Behave step" },
  { label: "@step('", type: "keyword" as const, detail: "Behave step" },
];

export function parseStepDefinitions(source: string, filePath: string): StepDefinition[] {
  const out: StepDefinition[] = [];
  let match: RegExpExecArray | null;
  const re = new RegExp(STEP_DECORATOR_RE.source, STEP_DECORATOR_RE.flags);
  while ((match = re.exec(source)) !== null) {
    const keyword = match[1].toLowerCase() as StepDefinition["keyword"];
    const text = match[3].replace(/\\(['"])/g, "$1").trim();
    if (text) out.push({ keyword, text, source: filePath });
  }
  return out;
}

export function parsePageMethods(source: string): string[] {
  const methods = new Set<string>();
  let match: RegExpExecArray | null;
  const re = new RegExp(PY_METHOD_RE.source, PY_METHOD_RE.flags);
  while ((match = re.exec(source)) !== null) {
    const name = match[1];
    if (name !== "__init__") methods.add(name);
  }
  return [...methods].sort();
}

export function parseFeatureNames(source: string): { features: string[]; scenarios: string[] } {
  const features: string[] = [];
  const scenarios: string[] = [];
  let match: RegExpExecArray | null;
  const fr = new RegExp(FEATURE_NAME_RE.source, FEATURE_NAME_RE.flags);
  while ((match = fr.exec(source)) !== null) {
    features.push(match[1].trim());
  }
  const sr = new RegExp(SCENARIO_NAME_RE.source, SCENARIO_NAME_RE.flags);
  while ((match = sr.exec(source)) !== null) {
    scenarios.push(match[1].trim());
  }
  return { features, scenarios };
}

export function parseJsonKeys(source: string, maxDepth = 2): string[] {
  try {
    const data = JSON.parse(source) as unknown;
    const keys = new Set<string>();
    const walk = (value: unknown, depth: number, prefix: string) => {
      if (depth > maxDepth || value == null || typeof value !== "object") return;
      if (Array.isArray(value)) {
        if (value.length > 0) walk(value[0], depth + 1, prefix);
        return;
      }
      for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
        const path = prefix ? `${prefix}.${k}` : k;
        keys.add(path);
        keys.add(k);
        walk(v, depth + 1, path);
      }
    };
    walk(data, 0, "");
    return [...keys].sort();
  } catch {
    return ["urls", "elements", "url", "selector", "selectors"];
  }
}

export function parseButtonFunctions(source: string): string[] {
  return parsePageMethods(source).filter((n) => !n.startsWith("_"));
}

export function stepsBaseName(stepsPath: string): string {
  const file = stepsPath.split("/").pop() ?? "";
  return file.replace(/_steps\.py$/i, "");
}

export function pageBaseName(pagePath: string): string {
  const file = pagePath.split("/").pop() ?? "";
  return file.replace(/_page\.py$/i, "");
}

function filterCompletions(items: Completion[], prefix: string): Completion[] {
  const lower = prefix.toLowerCase();
  return items.filter((item) => String(item.label).toLowerCase().startsWith(lower));
}

function completionResult(from: number, options: Completion[]): CompletionResult | null {
  if (options.length === 0) return null;
  return { from, options, validFor: /^[^\n]*$/ };
}

function featureCompletions(context: CompletionContext, project: ProjectAutocompleteContext): CompletionResult | null {
  const line = context.state.doc.lineAt(context.pos);
  const textBefore = line.text.slice(0, context.pos - line.from);

  const stepLine = textBefore.match(/^\s*(?:Given|When|Then|And|But|\*)\s+(.*)$/i);
  if (stepLine) {
    const prefix = stepLine[1];
    const from = context.pos - prefix.length;
    const options: Completion[] = project.steps
      .filter((s) => s.text.toLowerCase().includes(prefix.toLowerCase()))
      .map((s) => ({
        label: s.text,
        type: "text",
        detail: `${s.keyword} · ${s.source.split("/").pop()}`,
        apply: s.text,
      }));
    return completionResult(from, options);
  }

  if (/^\s*[A-Za-z][A-Za-z :]*$/.test(textBefore)) {
    const prefix = textBefore.trimStart();
    const from = line.from + (textBefore.length - prefix.length);
    const keywordOptions: Completion[] = GHERKIN_KEYWORDS.map((k) => ({
      label: k.label,
      type: k.type,
      detail: k.detail,
    }));
    const scenarioOptions: Completion[] = project.scenarioNames.map((name) => ({
      label: `Scenario: ${name}`,
      type: "text",
      detail: "Escenario existente",
      apply: `Scenario: ${name}`,
    }));
    return completionResult(from, [...keywordOptions, ...scenarioOptions].filter((o) =>
      String(o.label).toLowerCase().startsWith(prefix.toLowerCase()),
    ));
  }

  return null;
}

function stepsCompletions(
  context: CompletionContext,
  project: ProjectAutocompleteContext,
  filePath: string,
): CompletionResult | null {
  const line = context.state.doc.lineAt(context.pos);
  const textBefore = line.text.slice(0, context.pos - line.from);

  const pageMatch = textBefore.match(/context\.page\.([A-Za-z_][A-Za-z0-9_]*)$/);
  if (pageMatch) {
    const prefix = pageMatch[1];
    const base = stepsBaseName(filePath);
    const methods = project.pageMethods[base] ?? [];
    const from = context.pos - prefix.length;
    return completionResult(
      from,
      methods.map((m) => ({
        label: m,
        type: "method",
        detail: `Page ${base}_page`,
        apply: m,
      })).filter((o) => String(o.label).toLowerCase().startsWith(prefix.toLowerCase())),
    );
  }

  const decoratorMatch = textBefore.match(/@(given|when|then|step)\(\s*(['"])(.*)$/i);
  if (decoratorMatch) {
    const prefix = decoratorMatch[3];
    const from = context.pos - prefix.length;
    const kw = decoratorMatch[1].toLowerCase();
    const options = project.steps
      .filter((s) => s.keyword === kw || s.keyword === "step")
      .map((s) => ({
        label: s.text,
        type: "text",
        detail: s.source.split("/").pop(),
        apply: `${s.text}${decoratorMatch[2]})`,
      }));
    return completionResult(from, filterCompletions(options, prefix));
  }

  if (/^\s*@/.test(textBefore)) {
    const prefix = textBefore.trimStart();
    const from = line.from + (textBefore.length - prefix.length);
    return completionResult(from, filterCompletions(STEP_DECORATORS, prefix));
  }

  if (/^\s*(from utils\.button_functions import|from utils\.button_functions import \*)$/i.test(textBefore)) {
    const from = context.pos;
    return completionResult(from, project.buttonFunctions.slice(0, 40).map((fn) => ({
      label: fn,
      type: "function",
      detail: "button_functions",
    })));
  }

  return null;
}

function pageCompletions(context: CompletionContext, project: ProjectAutocompleteContext): CompletionResult | null {
  const line = context.state.doc.lineAt(context.pos);
  const textBefore = line.text.slice(0, context.pos - line.from);

  if (/^\s*def\s+[A-Za-z_][A-Za-z0-9_]*/.test(textBefore)) {
    return null;
  }

  if (/self\.([A-Za-z_][A-Za-z0-9_]*)$/.test(textBefore)) {
    const match = textBefore.match(/self\.([A-Za-z_][A-Za-z0-9_]*)$/);
    const prefix = match?.[1] ?? "";
    const from = context.pos - prefix.length;
    const locatorHints = ["self.driver", "self.click_", "self.fill_", "self.select_"];
    return completionResult(from, filterCompletions(
      locatorHints.map((h) => ({ label: h, type: "property", detail: "Page object" })),
      prefix,
    ));
  }

  return null;
}

function jsonCompletions(context: CompletionContext, project: ProjectAutocompleteContext): CompletionResult | null {
  const line = context.state.doc.lineAt(context.pos);
  const textBefore = line.text.slice(0, context.pos - line.from);
  const keyMatch = textBefore.match(/"([A-Za-z0-9_.]*)$/);
  if (!keyMatch) return null;
  const prefix = keyMatch[1];
  const from = context.pos - prefix.length;
  const keys = project.jsonKeys.length
    ? project.jsonKeys
    : ["urls", "elements", "url", "selector", "xpath", "name", "value"];
  return completionResult(
    from,
    keys.map((k) => ({
      label: k,
      type: "property",
      detail: "JSON ELIA",
      apply: `${k}"`,
    })).filter((o) => String(o.label).toLowerCase().startsWith(prefix.toLowerCase())),
  );
}

export function createEliaCompletionSource(project: ProjectAutocompleteContext, filePath: string) {
  return (context: CompletionContext): CompletionResult | null => {
    if (!filePath) return null;
    const lower = filePath.toLowerCase();
    if (lower.endsWith(".feature")) return featureCompletions(context, project);
    if (lower.includes("/steps/") && lower.endsWith(".py")) return stepsCompletions(context, project, filePath);
    if (lower.startsWith("pages/") && lower.endsWith(".py")) return pageCompletions(context, project);
    if (lower.endsWith(".json")) return jsonCompletions(context, project);
    return null;
  };
}

export async function buildProjectAutocompleteContext(
  files: { path: string }[],
  readContent: (path: string) => Promise<string>,
): Promise<ProjectAutocompleteContext> {
  const ctx: ProjectAutocompleteContext = {
    steps: [],
    pageMethods: {},
    scenarioNames: [],
    featureNames: [],
    jsonKeys: [],
    buttonFunctions: [],
  };

  await Promise.all(
    files.map(async (file) => {
      const path = file.path.replace(/\\/g, "/");
      const lower = path.toLowerCase();
      let content: string;
      try {
        content = await readContent(path);
      } catch {
        return;
      }

      if (lower.includes("/steps/") && lower.endsWith(".py")) {
        ctx.steps.push(...parseStepDefinitions(content, path));
      } else if (lower.startsWith("pages/") && lower.endsWith(".py")) {
        ctx.pageMethods[pageBaseName(path)] = parsePageMethods(content);
      } else if (lower.endsWith(".feature")) {
        const parsed = parseFeatureNames(content);
        ctx.featureNames.push(...parsed.features);
        ctx.scenarioNames.push(...parsed.scenarios);
      } else if (lower.startsWith("resources/data/") && lower.endsWith(".json")) {
        ctx.jsonKeys.push(...parseJsonKeys(content));
      } else if (lower === "utils/button_functions.py") {
        ctx.buttonFunctions = parseButtonFunctions(content);
      }
    }),
  );

  ctx.steps = dedupeSteps(ctx.steps);
  ctx.scenarioNames = [...new Set(ctx.scenarioNames)];
  ctx.featureNames = [...new Set(ctx.featureNames)];
  ctx.jsonKeys = [...new Set(ctx.jsonKeys)];
  return ctx;
}

function dedupeSteps(steps: StepDefinition[]): StepDefinition[] {
  const seen = new Set<string>();
  const out: StepDefinition[] = [];
  for (const s of steps) {
    const key = `${s.keyword}:${s.text}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(s);
  }
  return out;
}

/** Incorpora el buffer del editor (aún no guardado) al índice de sugerencias. */
export function patchContextWithEditor(
  ctx: ProjectAutocompleteContext,
  filePath: string,
  content: string,
): ProjectAutocompleteContext {
  if (!filePath.trim() || !content) return ctx;
  const path = filePath.replace(/\\/g, "/");
  const lower = path.toLowerCase();
  const next: ProjectAutocompleteContext = {
    ...ctx,
    steps: ctx.steps.filter((s) => s.source !== path),
    pageMethods: { ...ctx.pageMethods },
    scenarioNames: [...ctx.scenarioNames],
    featureNames: [...ctx.featureNames],
    jsonKeys: [...ctx.jsonKeys],
    buttonFunctions: [...ctx.buttonFunctions],
  };

  if (lower.includes("/steps/") && lower.endsWith(".py")) {
    next.steps = dedupeSteps([...next.steps, ...parseStepDefinitions(content, path)]);
  } else if (lower.startsWith("pages/") && lower.endsWith(".py")) {
    next.pageMethods[pageBaseName(path)] = parsePageMethods(content);
  } else if (lower.endsWith(".feature")) {
    const parsed = parseFeatureNames(content);
    next.featureNames = [...new Set([...next.featureNames, ...parsed.features])];
    next.scenarioNames = [...new Set([...next.scenarioNames, ...parsed.scenarios])];
  } else if (lower.startsWith("resources/data/") && lower.endsWith(".json")) {
    next.jsonKeys = [...new Set([...next.jsonKeys, ...parseJsonKeys(content)])];
  } else if (lower === "utils/button_functions.py") {
    next.buttonFunctions = parseButtonFunctions(content);
  }

  return next;
}
