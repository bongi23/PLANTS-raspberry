class Node:
    def __init__(self, value):
        self.val = value
        self.parent = None
        self.sons = {}

    def __int__(self):
        return self.val

    def __cmp__(self, other):
        return self.val - other.val

    def __str__(self):
        ret = str(self.val)
        for son in self.sons.values():
            ret += str(son)
        return ret


class RoutingTable:

    __ids = {
        2796262830: 'W',
        2426823503: 'A',
        2764293628: 'M'
    }

    def __init__(self):
        self.__routing_tree = Node(None)
        self.__routes = {}

    def __len__(self):
        return len(self.__routes)

    def __setitem__(self, key, value):
        self.__check_item(key, value)
        self.__add_item(key, value)

    def __getitem__(self, key):
        return self.__get_list(key)

    def __check_item(self, key, value):

        # if key in self.__routes:
        #     val = self.__routes[key]
        #     self.__remove_sons(val)

        i = len(value) - 1
        node = None
        while i >= 0:
            val = value[i]
            i -= 1
            if val in self.__routes and node is None:
                node = self.__routes[val]
            elif node is not None:
                if node.parent is not None and node.parent.val != val:
                    if node.parent.parent is not None:
                        node.parent.parent.sons.pop(node.parent.val)
                        node.parent.parent = None
                    self.__remove_sons(node.parent)
                    node = None
                else:
                    node = node.parent
        if node is not None:
            if node.parent is not None and node.parent.val is not None:
                node.parent.sons.pop(node.val)
                node.parent = None
                self.__remove_sons(node)

    def __remove_sons(self, node):
        for son in node.sons.values():
            son.parent = None
            self.__routes.pop(son.val)
            self.__remove_sons(son)
        node.sons = {}

    def __add_item(self, key, value):
        current = self.__routing_tree
        for node in value[:-1]:
            tmp = Node(node)
            if tmp.val not in current.sons:
                current.sons[tmp.val] = tmp
                tmp.parent = current
                self.__routes[node] = tmp
            current = current.sons[node]

        node = value[-1]
        tmp = Node(node)
        if tmp.val not in current.sons:
            current.sons[tmp.val] = tmp
            tmp.parent = current
        else:
            tmp = current.sons[tmp.val]
        self.__routes[key] = tmp

    def __get_list(self, key):
        ret = []
        node = self.__routes.get(key)
        while node is not None and node.val is not None:
            ret = [node.val] + ret
            node = node.parent
        return ret

    def __str__(self):
        s = ''
        for route in self.__routes:
            s += '{0}: ['.format(RoutingTable.__id_to_str(route))
            l = self.__get_list(route)
            for e in l[:-1]:
                s += '{0} -> '.format(RoutingTable.__id_to_str(e))
            s += '{0}]\n'.format(RoutingTable.__id_to_str(l[-1]))
        return s

    @staticmethod
    def __id_to_str(i: int) -> str:
        return RoutingTable.__ids[i]

    def reset(self):
        self.__routing_tree = Node(None)
        self.__routes = {}
