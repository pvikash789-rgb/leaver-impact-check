# Lab: round 1

A trial tenant with four accounts: an admin, `maker1`, `maker2` and `leaver1`. Each flow runs every 15 minutes and either sends an email to the admin or adds a row to a SharePoint list, so its last successful run is easy to see.

| Case | Built by | Runs on | Pattern |
|---|---|---|---|
| L-01 | leaver1 | leaver1's Outlook connection | Own login |
| L-02 | leaver1, co-owner maker1 | leaver1's Outlook connection | Co-owner doesn't change the connection |
| L-03 | leaver1, co-owner maker1 | maker1's Outlook connection (swapped) | Owner leaves, login is someone else's |
| L-04 | maker1 | maker1's Outlook connection | Control |
| L-05 | leaver1 | leaver1's SharePoint connection | Second connector |
| L-06 | leaver1, inside a solution | leaver1's Outlook connection, through a connection reference | Solution flow |

## Steps

1. Let every flow run cleanly for at least two hours.
2. Write down the expected result for each case, with the time.
3. In the Microsoft 365 admin center, open the leaver and choose **Block sign-in**. Change nothing else.
4. Read each flow's run history, the admin mailbox and the SharePoint list at +1 hour, +2 hours and the next morning.
5. Run `leaver_impact_check.py` for the leaver and compare its list with the flows that failed.

## Round 1 result (20 to 21 Oct 2026)

Predicted to fail: L-01, L-02, L-05, L-06. Predicted to keep working: L-03, L-04. All six matched. Timing prediction (up to 90 minutes) was wrong: the Outlook flows failed on the first run after the block. L-05 succeeded once, 37 minutes after the block, then failed.

The script listed exactly L-01, L-02, L-05 and L-06.

No data from the tenant is kept in this repository.
