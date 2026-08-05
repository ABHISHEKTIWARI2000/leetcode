class Solution(object):
    def findMissingElements(self, nums):
        """
        :type nums: List[int]
        :rtype: List[int]
        """
        nums.sort()
        #print nums
        small = nums[0]
        large = nums[len(nums)-1]
        ans = []
        j=0
        for i in range(small,large+1):
            if(i!=nums[j]):
                ans = ans + [i]
            else:
                j+=1
        return ans
        