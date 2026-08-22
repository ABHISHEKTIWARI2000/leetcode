class Solution(object):
    def findErrorNums(self, nums):
        """
        :type nums: List[int]
        :rtype: List[int]
        """
        n = len(nums)
        total = sum(nums)
        # print total
        diff = (n*(n+1))/2 - total
        l = 0
        double = 0 
        nums.sort()
        for i in nums:
            if(l == i):
                double = i
                break
            l = i
        res = []
        res.append(double)
        res.append(double + diff)
        return res