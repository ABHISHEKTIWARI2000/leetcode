from collections import defaultdict, deque
class Solution:
    def validPath(self, n: int, edges: list[list[int]], source: int, destination: int) -> bool:
        my_dict = defaultdict(list)
        for edge in edges:
            u = edge[0]
            v = edge[1]
            my_dict[u].append(v)
            my_dict[v].append(u)
        #print(my_dict)

        if source == destination:
            return True
        
        queue = deque([source])
        visited = {source}
        
        while queue:
            curr = queue.pop()
            
            if curr == destination:
                return True
            
            for C_node in my_dict[curr]:
                if C_node not in visited:
                    visited.add(C_node)
                    queue.append(C_node)
            
        return False
            