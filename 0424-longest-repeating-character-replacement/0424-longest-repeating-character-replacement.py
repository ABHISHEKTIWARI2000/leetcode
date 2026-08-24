class Solution(object):
    def characterReplacement(self, s, k):
        """
        :type s: str
        :type k: int
        :rtype: int
        """
        left, right = 0 , 0
        maxlen, mmf = 0, 0
        store = dict.fromkeys(range(27), 0)
        while(right < len(s)):
            store[ord(s[right])-ord("A")] += 1
            mmf = max(mmf, store[ord(s[right])-ord("A")])
            if((right - left - mmf +1) > k):
                store[ord(s[left])-ord("A")] -= 1
                # mmf=0
                left += 1
            if((right - left - mmf +1) <= k):
                maxlen = max(maxlen, (right - left + 1))
                # print(f"{maxlen} left = {left} right = {right}")
                right += 1
        return maxlen