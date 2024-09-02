# 
## IAM MANAGEMENT

## AUCTIONING SYSTEM


AUCTION SYSTEM MVP
this is web app is design for artists, especially for small or starting artist.
where they can create auction event, create auction item set base price


After having a user and profile
An Artist can create an Auction Event

AUCTION table
id: UUID
name: str : "CINOS 1st Auction"
owner: UUID: USER_ID
event_type: public or private ( not sure how make this enum)
thumbnail: URL STRING
duration: 1 day
visits: int
start_datetime: datetime : sept 7, 2024 9pm
end_datetime: datetime: sept 8, 2024 9pm


now after the event has been created, the artist can now create auction items.

AUCTION_ITEM table
ID: UUID
auction_id: UUID of auction
owner: user_id
name: str: OMAD PRIME
primary_photo: url string
gallery: [
    url strings
    url strings
]
description: long str: description of the auction item
base_price: 9,9999
views: int

Maybe Create something like this


Auction System,
Every Auction Item is visible for everyone if public, and the bids should be live for everyone.
so there will be like a live websocket that tracks the user bids and get's displayed for UI

user a bid 10,000
user b bid 12,000
user a bid 13,000

then when the schedule ends the highest bidder has 2 hours to pay and the item will be locked.

