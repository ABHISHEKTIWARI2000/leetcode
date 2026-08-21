class Solution(object):
    def findMaxConsecutiveOnes(self, nums):
        """
        :type nums: List[int]
        :rtype: int
        """
        sub0 = 0
        res = 0
        for i in nums:
            if i == 1:
                sub0 += 1
            else:
                # print sub0
                res = max(res,sub0)
                sub0 = 0
        res = max(res,sub0)
        return res