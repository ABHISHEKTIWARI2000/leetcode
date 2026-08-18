class Solution(object):
    def minWindow(self, s, t):
        slen = len(s)
        creq = len(t)
        res = ""
        if slen < creq:
            return res
        windowSize = pow(10,5)+1
        i = 0
        j = 0
        charCnt = {}
        for char in t:
            charCnt[char] = charCnt.get(char, 0) + 1
        while(j<slen):
            while(creq > 0 and j<slen):
                if(charCnt.get(s[j],0) > 0):
                    creq -= 1
                charCnt[s[j]] = charCnt.get(s[j],0)-1
                j += 1
            if((j-i+1) < int(windowSize) and creq == 0):
                res = s[i:j]
                windowSize = j-i+1
            
            while(creq == 0 and i<j):
                if(charCnt.get(s[i]) >= 0):
                    creq += 1
                else:
                    if((j-i) < int(windowSize) and creq == 0):
                        res = s[i+1:j]
                        windowSize = j-i
                charCnt[s[i]] += 1
                i += 1
            
        return res
