class BPlusTreeNode:
    def __init__(self, order, is_leaf=True):
        self.order = order
        self.is_leaf = is_leaf
        self.keys = []
        self.values = []
        self.children = []
        self.next = None

    def is_full(self):
        return len(self.keys) >= self.order - 1

class BPlusTree:
    def __init__(self, order=8):
        self.order = order
        self.root = BPlusTreeNode(order)

    def search(self, key):
        return self._search(self.root, key)

    def _search(self, node, key):
        i = 0
        while i < len(node.keys) and key > node.keys[i]:
            i += 1
        if node.is_leaf:
            if i < len(node.keys) and node.keys[i] == key:
                return node.values[i]
            return None
        if i < len(node.keys) and node.keys[i] == key:
            i += 1
        return self._search(node.children[i], key)

    def insert(self, key, value):
        root = self.root
        if root.is_full():
            new_root = BPlusTreeNode(self.order, is_leaf=False)
            new_root.children.append(self.root)
            self._split_child(new_root, 0)
            self.root = new_root
        self._insert_non_full(self.root, key, value)

    def _insert_non_full(self, node, key, value):
        i = len(node.keys) - 1
        if node.is_leaf:
            while i >= 0 and key < node.keys[i]:
                i -= 1
            if i >= 0 and key == node.keys[i]:
                node.values[i] = value # Just update in-place for simplistic insert
                return
            node.keys.insert(i + 1, key)
            node.values.insert(i + 1, value)
        else:
            while i >= 0 and key < node.keys[i]:
                i -= 1
            i += 1
            if node.children[i].is_full():
                self._split_child(node, i)
                if key > node.keys[i]:
                    i += 1
            self._insert_non_full(node.children[i], key, value)

    def _split_child(self, parent, index):
        child = parent.children[index]
        new_child = BPlusTreeNode(self.order, child.is_leaf)
        mid = len(child.keys) // 2

        if child.is_leaf:
            new_child.keys = child.keys[mid:]
            new_child.values = child.values[mid:]
            child.keys = child.keys[:mid]
            child.values = child.values[:mid]
            new_child.next = child.next
            child.next = new_child
            parent.keys.insert(index, new_child.keys[0])
            parent.children.insert(index + 1, new_child)
        else:
            new_child.keys = child.keys[mid + 1:]
            new_child.children = child.children[mid + 1:]
            up_key = child.keys[mid]
            child.keys = child.keys[:mid]
            child.children = child.children[:mid + 1]
            parent.keys.insert(index, up_key)
            parent.children.insert(index + 1, new_child)

    def delete(self, key):
        if self.root is None:
            return False

        deleted = self._delete(self.root, key)

        if not self.root.is_leaf and len(self.root.keys) == 0 and self.root.children:
            self.root = self.root.children[0]

        return deleted

    def _delete(self, node, key):
        if node.is_leaf:
            try:
                idx = node.keys.index(key)
            except ValueError:
                return False

            node.keys.pop(idx)
            node.values.pop(idx)
            return True

        idx = 0
        while idx < len(node.keys) and key >= node.keys[idx]:
            idx += 1

        deleted = self._delete(node.children[idx], key)
        if not deleted:
            return False

        self._fill_child(node, idx)

        # Keep separator keys aligned to first key of each right child.
        for i in range(len(node.keys)):
            right_child = node.children[i + 1]
            if right_child.keys:
                node.keys[i] = right_child.keys[0]

        return True

    def _min_leaf_keys(self):
        return self.order // 2

    def _min_internal_keys(self):
        return max(1, (self.order + 1) // 2 - 1)

    def _fill_child(self, node, index):
        child = node.children[index]
        min_keys = self._min_leaf_keys() if child.is_leaf else self._min_internal_keys()

        if len(child.keys) >= min_keys:
            return

        if index > 0 and len(node.children[index - 1].keys) > min_keys:
            self._borrow_from_prev(node, index)
        elif index < len(node.children) - 1 and len(node.children[index + 1].keys) > min_keys:
            self._borrow_from_next(node, index)
        else:
            if index < len(node.children) - 1:
                self._merge(node, index)
            else:
                self._merge(node, index - 1)

    def _borrow_from_prev(self, node, index):
        child = node.children[index]
        left = node.children[index - 1]

        if child.is_leaf:
            child.keys.insert(0, left.keys.pop())
            child.values.insert(0, left.values.pop())
            node.keys[index - 1] = child.keys[0]
            return

        child.keys.insert(0, node.keys[index - 1])
        node.keys[index - 1] = left.keys.pop()
        child.children.insert(0, left.children.pop())

    def _borrow_from_next(self, node, index):
        child = node.children[index]
        right = node.children[index + 1]

        if child.is_leaf:
            child.keys.append(right.keys.pop(0))
            child.values.append(right.values.pop(0))
            if right.keys:
                node.keys[index] = right.keys[0]
            return

        child.keys.append(node.keys[index])
        node.keys[index] = right.keys.pop(0)
        child.children.append(right.children.pop(0))

    def _merge(self, node, index):
        left = node.children[index]
        right = node.children[index + 1]

        if left.is_leaf:
            left.keys.extend(right.keys)
            left.values.extend(right.values)
            left.next = right.next
        else:
            left.keys.append(node.keys[index])
            left.keys.extend(right.keys)
            left.children.extend(right.children)

        node.keys.pop(index)
        node.children.pop(index + 1)

    def update(self, key, new_value):
        existing = self.search(key)
        if existing is None:
            return False
        self.insert(key, new_value)
        return True

    def range_query(self, start_key, end_key):
        curr = self.root
        while not curr.is_leaf:
            i = 0
            while i < len(curr.keys) and start_key >= curr.keys[i]:
                i += 1
            curr = curr.children[i]
        
        results = []
        while curr is not None:
            for i in range(len(curr.keys)):
                if curr.keys[i] >= start_key and curr.keys[i] <= end_key:
                    results.append((curr.keys[i], curr.values[i]))
                elif curr.keys[i] > end_key:
                    return results
            curr = curr.next
        return results

    def get_all(self):
        curr = self.root
        while not curr.is_leaf:
            curr = curr.children[0]
        results = []
        while curr is not None:
            for i in range(len(curr.keys)):
                results.append((curr.keys[i], curr.values[i]))
            curr = curr.next
        return results

    def visualize_tree(self, filename=None):
        from graphviz import Digraph

        dot = Digraph(comment='B+ Tree')
        dot.attr('node', shape='record', fontsize='10')

        self._add_nodes(dot, self.root)
        self._add_edges(dot, self.root)

        if filename:
            dot.render(filename, cleanup=True)
        return dot

    def _add_nodes(self, dot, node):
        node_id = str(id(node))
        keys_label = ' | '.join(str(k) for k in node.keys) if node.keys else 'empty'
        leaf_tag = 'leaf' if node.is_leaf else 'internal'
        dot.node(node_id, f"{leaf_tag} | {keys_label}")

        if not node.is_leaf:
            for child in node.children:
                self._add_nodes(dot, child)

    def _add_edges(self, dot, node):
        if node.is_leaf:
            if node.next is not None:
                dot.edge(str(id(node)), str(id(node.next)), style='dashed', color='gray')
            return

        for child in node.children:
            dot.edge(str(id(node)), str(id(child)))
            self._add_edges(dot, child)
