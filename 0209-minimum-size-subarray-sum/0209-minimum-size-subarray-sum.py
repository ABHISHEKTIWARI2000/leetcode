class Solution(object):
    def minSubArrayLen(self, target, nums):
        """
        :type target: int
        :type nums: List[int]
        :rtype: int
        """
        sum = 0
        ws = float('inf')
        i=0
        j=0
        n = len(nums)
        while(j < n):
            while(sum < target and j < n):
                sum += nums[j]
                j  += 1
            while(sum >= target):
                ws = min(ws , j-i)
                sum -= nums[i]
                i += 1
        if(ws == float('inf')):
            ws = 0
        return ws
            
        