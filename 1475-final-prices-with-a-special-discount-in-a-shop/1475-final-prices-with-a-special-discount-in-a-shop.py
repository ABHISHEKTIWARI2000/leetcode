class Solution:
    def finalPrices(self, prices: List[int]) -> List[int]:
        n = len(prices)
        answer = prices[:]
        monostack = [prices[n-1]]
        answer[n-1] = prices[n-1]
        for i in range(n-2,-1,-1):
            for j in range(len(monostack)-1,-1,-1):
                if(prices[i] >= monostack[j]):
                    # print(f"{i} -> j = {j} {prices[i]} - {monostack[j]} ")
                    answer[i] = prices[i] - monostack[j]
                    # print(prices[i])
                    break
            monostack.append(prices[i])
            # print(monostack)

        return answer