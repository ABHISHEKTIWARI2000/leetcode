class Solution:
    def evalRPN(self, tokens: List[str]) -> int:
        stack = []
        for i in tokens:
            if i.lstrip('-').isnumeric():
                stack.append(int(i))
            else:
                match i:
                    case '+':
                        # print("Addition")
                        res = stack[-2] + stack[-1]
                        stack.pop()
                        stack.pop()
                        stack.append(res)
                    case '-':
                        # print("Subtraction")
                        res = stack[-2] - stack[-1]
                        stack.pop()
                        stack.pop()
                        stack.append(res)
                    case '*':
                        # print("Multiplication")
                        res = stack[-2] * stack[-1]
                        stack.pop()
                        stack.pop()
                        stack.append(res)
                    case '/':
                        # print("Division")
                        res = int(stack[-2] / stack[-1])
                        stack.pop()
                        stack.pop()
                        stack.append(res)
        return stack[0]