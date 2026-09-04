class Solution:
    def timeRequiredToBuy(self, tickets: List[int], k: int) -> int:
        answer = 0
        for i, val in enumerate(tickets):
            if(i<=k):
                answer += min(val,tickets[k])
            else:
                answer += min(val,tickets[k]-1)
        return answer