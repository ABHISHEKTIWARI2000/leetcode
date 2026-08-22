class Solution(object):
    def findDisappearedNumbers(self, nums):
        """
        :type nums: List[int]
        :rtype: List[int]
        """
        res = []
        helper = {}
        maxi = 0
        for i in nums:
            helper[i] = helper.get(i,0) + 1
        
        for i in range(1,len(nums)+1):
            if i not in helper:
                res.append(i)
        return res
        
        