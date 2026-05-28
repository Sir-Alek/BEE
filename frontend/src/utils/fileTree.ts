export type FileTreeNode = {
  name: string;
  path?: string;
  children?: FileTreeNode[];
};

export function buildFileTree(files: { path: string; name: string }[]): FileTreeNode[] {
  type MapNode = { children: Map<string, MapNode>; filePath?: string };
  const root = new Map<string, MapNode>();

  for (const f of files) {
    const parts = f.path.replace(/\\/g, "/").split("/").filter(Boolean);
    let current = root;
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (!current.has(part)) current.set(part, { children: new Map() });
      const node = current.get(part)!;
      if (i === parts.length - 1) node.filePath = f.path;
      current = node.children;
    }
  }

  const toArray = (map: Map<string, MapNode>): FileTreeNode[] =>
    [...map.entries()]
      .sort(([nameA, nodeA], [nameB, nodeB]) => {
        const folderA = nodeA.children.size > 0;
        const folderB = nodeB.children.size > 0;
        if (folderA !== folderB) return folderA ? -1 : 1;
        return nameA.localeCompare(nameB);
      })
      .map(([name, node]) => {
        const childArr = node.children.size ? toArray(node.children) : undefined;
        return {
          name,
          path: node.filePath,
          children: childArr?.length ? childArr : undefined,
        };
      });

  return toArray(root);
}
