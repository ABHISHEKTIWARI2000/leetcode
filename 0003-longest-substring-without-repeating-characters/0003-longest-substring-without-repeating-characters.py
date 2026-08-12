class Solution(object):
    def lengthOfLongestSubstring(self, s):
        n = len(s)
        if(n == 0 or n == 1):
            return n
        countChar = {}
        i = 0
        j = 0
        out = 0
        res = 0
        while(j<n):
            count = countChar.get(s[j],0)
            if(count == 0):
                res += 1
                countChar[s[j]] = count + 1
                j += 1
                out = max(out, res)
            else:
                countChar[s[i]] = countChar.get(s[i],0) - 1
                i += 1
                res -= 1
        return out
