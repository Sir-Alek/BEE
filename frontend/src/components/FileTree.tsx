import React, { useMemo, useState } from "react";
import { buildFileTree, type FileTreeNode } from "../utils/fileTree";

type Props = {
  c: Record<string, string>;
  files: { path: string; name: string }[];
  selectedPath: string;
  onSelectFile: (path: string) => void;
};

export function FileTree(props: Props) {
  const { c, files, selectedPath, onSelectFile } = props;
  const tree = useMemo(() => buildFileTree(files), [files]);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  if (files.length === 0) {
    return <div style={{ padding: 10, color: c.muted }}>Sin archivos editables</div>;
  }

  return (
    <div data-testid="elia-file-tree" style={{ padding: "4px 0" }}>
      {tree.map((node) => (
        <TreeBranch
          key={node.path ?? node.name}
          c={c}
          node={node}
          depth={0}
          prefix=""
          selectedPath={selectedPath}
          collapsed={collapsed}
          onToggle={(key) => setCollapsed((prev) => ({ ...prev, [key]: !prev[key] }))}
          onSelectFile={onSelectFile}
        />
      ))}
    </div>
  );
}

function TreeBranch(props: {
  c: Record<string, string>;
  node: FileTreeNode;
  depth: number;
  prefix: string;
  selectedPath: string;
  collapsed: Record<string, boolean>;
  onToggle: (key: string) => void;
  onSelectFile: (path: string) => void;
}) {
  const { c, node, depth, prefix, selectedPath, collapsed, onToggle, onSelectFile } = props;
  const key = prefix ? `${prefix}/${node.name}` : node.name;
  const isFolder = !!node.children?.length;
  const isCollapsed = collapsed[key] ?? false;

  if (!isFolder && node.path) {
    const active = selectedPath === node.path;
    return (
      <button
        type="button"
        data-testid={`elia-file-tree-item-${node.path.replace(/[/\\]/g, "_")}`}
        title={node.path}
        onClick={() => onSelectFile(node.path!)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          width: "100%",
          textAlign: "left",
          padding: "6px 10px",
          paddingLeft: 10 + depth * 14,
          border: "none",
          background: active ? c.neutralBg : "transparent",
          color: active ? c.primary : c.text,
          cursor: "pointer",
          fontSize: 12,
        }}
      >
        <span style={{ color: c.muted, width: 14 }}>📄</span>
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{node.name}</span>
      </button>
    );
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => onToggle(key)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          width: "100%",
          textAlign: "left",
          padding: "6px 10px",
          paddingLeft: 10 + depth * 14,
          border: "none",
          background: "transparent",
          color: c.text,
          cursor: "pointer",
          fontSize: 12,
          fontWeight: 600,
        }}
      >
        <span style={{ color: c.muted, width: 14, fontSize: 10 }}>{isCollapsed ? "▸" : "▾"}</span>
        <span style={{ color: c.muted }}>📁</span>
        <span>{node.name}</span>
      </button>
      {!isCollapsed
        ? node.children?.map((child) => (
            <TreeBranch
              key={child.path ?? `${key}/${child.name}`}
              c={c}
              node={child}
              depth={depth + 1}
              prefix={key}
              selectedPath={selectedPath}
              collapsed={collapsed}
              onToggle={onToggle}
              onSelectFile={onSelectFile}
            />
          ))
        : null}
    </div>
  );
}
