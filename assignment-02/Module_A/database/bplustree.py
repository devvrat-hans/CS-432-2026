from graphviz import Digraph


class BPlusTreeNode:
    def __init__(self, leaf=False):
        self.leaf = leaf
        self.keys = []
        self.children = []
        self.values = []
        self.next = None


class BPlusTree:
    def __init__(self, t=3):
        self.root = BPlusTreeNode(leaf=True)
        self.t = t

    # ---------------- SEARCH ----------------
    def search(self, key, node=None):
        if node is None:
            node = self.root

        if node.leaf:
            for i, k in enumerate(node.keys):
                if k == key:
                    return node.values[i]
            return None

        i = 0
        while i < len(node.keys) and key >= node.keys[i]:
            i += 1
        return self.search(key, node.children[i])

    # ---------------- INSERT ----------------
    def insert(self, key, value):
        # Handle duplicate
        if self.search(key) is not None:
            self.update(key, value)
            return

        root = self.root

        if len(root.keys) == (2 * self.t - 1):
            new_root = BPlusTreeNode()
            new_root.children.append(root)
            self._split_child(new_root, 0)
            self.root = new_root

        self._insert_non_full(self.root, key, value)

    def _insert_non_full(self, node, key, value):
        if node.leaf:
            i = len(node.keys) - 1

            node.keys.append(None)
            node.values.append(None)

            while i >= 0 and key < node.keys[i]:
                node.keys[i + 1] = node.keys[i]
                node.values[i + 1] = node.values[i]
                i -= 1

            node.keys[i + 1] = key
            node.values[i + 1] = value

        else:
            i = len(node.keys) - 1
            while i >= 0 and key < node.keys[i]:
                i -= 1
            i += 1

            if len(node.children[i].keys) == (2 * self.t - 1):
                self._split_child(node, i)

                if key > node.keys[i]:
                    i += 1

            self._insert_non_full(node.children[i], key, value)

    def _split_child(self, parent, index):
        node = parent.children[index]
        new_node = BPlusTreeNode(leaf=node.leaf)
        t = self.t
        mid = t - 1

        if node.leaf:
            new_node.keys = node.keys[mid:]
            new_node.values = node.values[mid:]

            node.keys = node.keys[:mid]
            node.values = node.values[:mid]

            # Maintain leaf linkage
            new_node.next = node.next
            node.next = new_node

            parent.keys.insert(index, new_node.keys[0])
            parent.children.insert(index + 1, new_node)

        else:
            parent.keys.insert(index, node.keys[mid])

            new_node.keys = node.keys[mid + 1:]
            node.keys = node.keys[:mid]

            new_node.children = node.children[mid + 1:]
            node.children = node.children[:mid + 1]

            parent.children.insert(index + 1, new_node)

    # ---------------- DELETE ----------------
    def delete(self, key):
        if self.search(key) is None:
            return False

        self._delete(self.root, key)

        # Update root if empty
        if not self.root.leaf and len(self.root.keys) == 0:
            self.root = self.root.children[0]

        return True

    def _delete(self, node, key):
        if node.leaf:
            if key in node.keys:
                idx = node.keys.index(key)
                node.keys.pop(idx)
                node.values.pop(idx)
            return

        idx = 0
        while idx < len(node.keys) and key >= node.keys[idx]:
            idx += 1

        child = node.children[idx]

        if len(child.keys) < (self.t - 1):
            self._fill_child(node, idx)

        self._delete(node.children[idx], key)

    def _fill_child(self, node, idx):
        if idx > 0 and len(node.children[idx - 1].keys) >= self.t:
            self._borrow_from_prev(node, idx)
        elif idx < len(node.children) - 1 and len(node.children[idx + 1].keys) >= self.t:
            self._borrow_from_next(node, idx)
        else:
            if idx < len(node.children) - 1:
                self._merge(node, idx)
            else:
                self._merge(node, idx - 1)

    def _borrow_from_prev(self, node, idx):
        child = node.children[idx]
        sibling = node.children[idx - 1]

        if child.leaf:
            child.keys.insert(0, sibling.keys.pop(-1))
            child.values.insert(0, sibling.values.pop(-1))
            node.keys[idx - 1] = child.keys[0]
        else:
            child.keys.insert(0, node.keys[idx - 1])
            node.keys[idx - 1] = sibling.keys.pop(-1)
            child.children.insert(0, sibling.children.pop(-1))

    def _borrow_from_next(self, node, idx):
        child = node.children[idx]
        sibling = node.children[idx + 1]

        if child.leaf:
            child.keys.append(sibling.keys.pop(0))
            child.values.append(sibling.values.pop(0))
            node.keys[idx] = sibling.keys[0]
        else:
            child.keys.append(node.keys[idx])
            node.keys[idx] = sibling.keys.pop(0)
            child.children.append(sibling.children.pop(0))

    def _merge(self, node, idx):
        child = node.children[idx]
        sibling = node.children[idx + 1]

        if child.leaf:
            child.keys.extend(sibling.keys)
            child.values.extend(sibling.values)
            child.next = sibling.next
        else:
            child.keys.append(node.keys[idx])
            child.keys.extend(sibling.keys)
            child.children.extend(sibling.children)

        node.keys.pop(idx)
        node.children.pop(idx + 1)

    # ---------------- UPDATE ----------------
    def update(self, key, new_value):
        node = self.root

        while not node.leaf:
            i = 0
            while i < len(node.keys) and key >= node.keys[i]:
                i += 1
            node = node.children[i]

        for i, k in enumerate(node.keys):
            if k == key:
                node.values[i] = new_value
                return True

        return False

    # ---------------- RANGE QUERY ----------------
    def range_query(self, start_key, end_key):
        node = self.root

        # Go to first relevant leaf
        while not node.leaf:
            i = 0
            while i < len(node.keys) and start_key >= node.keys[i]:
                i += 1
            node = node.children[i]

        result = []

        # Traverse linked leaves
        while node:
            for i, k in enumerate(node.keys):
                if start_key <= k <= end_key:
                    result.append((k, node.values[i]))
                elif k > end_key:
                    return result
            node = node.next

        return result

    # ---------------- GET ALL ----------------
    def get_all(self):
        node = self.root

        while not node.leaf:
            node = node.children[0]

        result = []
        while node:
            for i in range(len(node.keys)):
                result.append((node.keys[i], node.values[i]))
            node = node.next

        return result

    # # ---------------- VISUALIZATION ----------------
    # def visualize_tree(self):
    #     dot = Digraph()
    #     self._add_nodes(dot, self.root)
    #     self._add_edges(dot, self.root)
    #     return dot

    # def _add_nodes(self, dot, node):
    #     node_id = str(id(node))
    #     if node.leaf:
    #         label = "Leaf\n" + "|".join(f"{k}:{v}" for k, v in zip(node.keys, node.values))
    #     else:
    #         label = "Internal\n" + "|".join(map(str, node.keys))

    #     dot.node(node_id, label)

    #     if not node.leaf:
    #         for child in node.children:
    #             self._add_nodes(dot, child)

    # def _add_edges(self, dot, node):
    #     node_id = str(id(node))

    #     if not node.leaf:
    #         for child in node.children:
    #             dot.edge(node_id, str(id(child)))
    #             self._add_edges(dot, child)

    #     # Leaf linkage (dashed)
    #     if node.leaf and node.next:
    #         dot.edge(node_id, str(id(node.next)), style="dashed
    def visualize_tree(self):
        dot = Digraph()
        dot.attr(rankdir='TB')  # Top to Bottom layout
    
        self._add_nodes(dot, self.root)
        self._add_edges(dot, self.root)
        self._link_leaves(dot)   # NEW: separate leaf linkage
    
        return dot
    
    
    def _add_nodes(self, dot, node):
        node_id = str(id(node))
    
        # Better label formatting
        if node.leaf:
            label = "{Leaf | " + " | ".join(f"{k}" for k in node.keys) + "}"
        else:
            label = "{Internal | " + " | ".join(map(str, node.keys)) + "}"
    
        dot.node(node_id, label, shape="record")
    
        if not node.leaf:
            for child in node.children:
                self._add_nodes(dot, child)
    
    
    def _add_edges(self, dot, node):
        node_id = str(id(node))
    
        if not node.leaf:
            for child in node.children:
                child_id = str(id(child))
                dot.edge(node_id, child_id)   # parent-child
                self._add_edges(dot, child)
    
    
    # 🔥 NEW FUNCTION (IMPORTANT FOR PROFESSOR REQUIREMENT)
    def _link_leaves(self, dot):
        # Go to leftmost leaf
        node = self.root
        while not node.leaf:
            node = node.children[0]
    
        # Traverse all leaves
        while node and node.next:
            dot.edge(
                str(id(node)),
                str(id(node.next)),
                style="dashed",
                color="blue",
                label="next"
            )
            node = node.next