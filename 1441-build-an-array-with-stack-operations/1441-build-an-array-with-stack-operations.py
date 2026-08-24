class Solution:
    def buildArray(self, target: List[int], n: int) -> List[str]:
        res = []
        target_idx, temp_data, res_idx = 0, 1, 0
        while(target_idx < len(target)):
            if(temp_data != target[target_idx]):
                res.extend(["Push", "Pop"])
                temp_data += 1
            else:
                res.extend(["Push"])
                temp_data += 1
                target_idx += 1 
        return res   