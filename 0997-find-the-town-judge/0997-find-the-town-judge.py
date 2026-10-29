class Solution:
    def findJudge(self, n: int, trust: list[list[int]]) -> int:
        candidate = [False]*n

        for label in trust:

            if(candidate[label[0]-1]==False):
                candidate[label[0]-1] = True
        
        result = -1
        for judge in range(1,len(candidate)+1):
            if(candidate[judge-1]==False):
                count = 0
                for label in trust:
                    if(label[1] == judge):
                        count+=1
                if(count == n-1):
                    return judge
        return -1