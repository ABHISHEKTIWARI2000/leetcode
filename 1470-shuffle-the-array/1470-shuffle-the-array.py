class Solution(object):
    def shuffle(self, nums, n):
        """
        :type nums: List[int]
        :type n: int
        :rtype: List[int]
        """
        i = 0
        j = n
        res = []
        while(i<n and j<2*n):
            res.append(nums[i])
            res.append(nums[j])
            i+=1
            j+=1
        return res
        