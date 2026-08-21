class Solution(object):
    def shuffle(self, nums, n):
        """
        :type nums: List[int]
        :type n: int
        :rtype: List[int]
        """
        i = 0
        res = []
        while(i<n):
            res.append(nums[i])
            res.append(nums[i+n])
            i+=1
        return res
        