# Write your MySQL query statement below
select
    DATE_FORMAT(trans_date, '%Y-%m') As month,
    country,
    count(id) As trans_count,
    Sum(if(state = 'approved', 1,0)) As approved_count,
    Sum(amount) as trans_total_amount,
    Sum(if(state='approved',amount,0)) as approved_total_amount
from Transactions
group by month, country;
