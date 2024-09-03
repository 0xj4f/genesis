# 
## IAM MANAGEMENT

2 default users role

- admin: can do everything
- user: read items



I think I need thave some mock data first that I can test. 
it looks something like this, if you can suggest better I'm open for suggestions.
```Yaml
- username: genesis-admin
  user_role: admin
  group_role: admin
  status: active

- username: genesis-staff
  user_role: user
  group_role: admin
  status: active

- username: ecom-user
  user_role: user
  group_role: customer
  status: active

- username: richie
  user_role: user
  group_role: customer
  status: active

- username: auction_user
  user_role: user
  group_role: auction_user
  status: active

- username: auction_artist
  user_role: user
  group_role: auction_artist
  status: active

- username: cinos
  user_role: user
  group_role: auction_artist
  status: active
```

And this is the mock data I was thinking for the permissions and roles. 
please fill them up so I can see and connect the data

roles:
- admin
- staff 
- user
- customer
- auction_user
- auction_artist

permissions:

auction_artist:
- create_auction_event ( LIST CRUD )
- create_auction_item ( LIST CRUD )
...  please  populate this with things you think best for this



## AUCTIONING SYSTEM


AUCTION SYSTEM MVP
this is web app is design for artists, especially for small or starting artist.
where they can create auction event, create auction item set base price.


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

### Auction System MVP: System Architecture, User Experience, and Data Structure

**Objective**: Create an Auction System MVP tailored for artists to auction their artwork. The system will allow artists to create auction events, list items, and conduct real-time bidding.

### 1. **System Architecture**

#### Components:
1. **Backend (FastAPI)**
   - **API Layer**: Handles RESTful API endpoints for user management, auction event management, and bidding.
   - **WebSocket Layer**: Manages real-time bid updates and notifications.
   - **Database Layer**: PostgreSQL for relational data storage.

2. **Frontend (Vue.js)**
   - **User Interface**: Provides a responsive and intuitive interface for users to create auctions, bid on items, and manage profiles.
   - **WebSocket Client**: Receives real-time bid updates and notifications.

3. **Database (PostgreSQL)**
   - Store structured data for users, profiles, auctions, and bids.
   - Use JSONB or arrays for storing gallery images for flexibility.

4. **Authentication & Authorization**
   - OAuth2 or JWT-based authentication to secure API endpoints.
   - Role-based access control to differentiate between artists, bidders, and admins.

5. **WebSocket Server**
   - Handles real-time communication for live bidding sessions.

6. **Task Scheduler (e.g., Celery, APScheduler)**
   - Manages auction start and end times, and sends notifications for bid reminders and payment deadlines.

### 2. **User Experience**

1. **Registration and Profile Setup**
   - Artists and bidders can register, create a profile, and verify their identity.

2. **Auction Event Creation**
   - Artists can create auction events, specify event details (public/private), and upload a thumbnail.

3. **Auction Item Listing**
   - Artists can list items for auction, set a base price, and upload multiple images to the gallery.

4. **Live Bidding Interface**
   - Users can view auction items, place bids, and see real-time bid updates.
   - Bidding history is visible, showing user bids.

5. **Auction Completion**
   - When an auction ends, the highest bidder is notified and given a set time to complete the payment.
   - Automatic reminders are sent to bidders close to the auction end.

### 3. **Data Structure**

**1. Users and Profiles (Existing)**

- **User Table**: 
  - `id: UUID`
  - `username: str`
  - `email: str`
  - `password: str`
  - `disabled: bool`

- **Profile Table**: 
  - `id: UUID`
  - `user_id: UUID (FK to User)`
  - `given_name: str`
  - `family_name: str`
  - `nick_name: str`
  - `picture: URL`
  - `email: str`
  - `sub: str`

**2. Auction Event**

- **Auction Table**:
  - `id: UUID`
  - `name: str`
  - `owner: UUID (FK to User)`
  - `event_type: enum('public', 'private')`
  - `thumbnail: str (URL)`
  - `duration: interval`
  - `visits: int`
  - `start_datetime: datetime`
  - `end_datetime: datetime`

  - **Enum for Event Type**:
    - Use PostgreSQL's ENUM type or define it in your application code using a choice field.

**3. Auction Item**

- **Auction Item Table**:
  - `id: UUID`
  - `auction_id: UUID (FK to Auction)`
  - `owner: UUID (FK to User)`
  - `name: str`
  - `primary_photo: str (URL)`
  - `gallery: JSONB` (Array of strings for URLs)
  - `description: text`
  - `base_price: decimal(10,2)`
  - `views: int`

**4. Bids**

- **Bids Table**:
  - `id: UUID`
  - `auction_item_id: UUID (FK to AuctionItem)`
  - `user_id: UUID (FK to User)`
  - `bid_amount: decimal(10,2)`
  - `bid_time: datetime`

**5. Notifications and Payments**

- **Notifications Table** (Optional):
  - `id: UUID`
  - `user_id: UUID (FK to User)`
  - `message: text`
  - `sent_at: datetime`

- **Payments Table** (Future Scope):
  - `id: UUID`
  - `user_id: UUID (FK to User)`
  - `auction_item_id: UUID (FK to AuctionItem)`
  - `amount: decimal(10,2)`
  - `payment_status: enum('pending', 'completed', 'failed')`
  - `payment_due: datetime`

### 4. **Implementation Plan**

1. **Setup Backend Infrastructure (FastAPI)**
   - Implement the foundational user management using existing User and Profile services.
   - Extend the service to handle auction events and auction items.

2. **Database Schema Design**
   - Create necessary tables in PostgreSQL based on the data structure.
   - Utilize foreign key constraints to maintain relational integrity.

3. **Auction Event and Item Management**
   - Create endpoints for creating, viewing, updating, and deleting auction events.
   - Similarly, manage auction items within an auction event.

4. **Real-time Bidding with WebSocket**
   - Implement WebSocket communication for live updates on bids.
   - Use channels/rooms to manage different auction events.

5. **Frontend Development (Vue.js)**
   - Develop a responsive UI for users to interact with the system.
   - Implement authentication and integrate with the backend API.
   - Use WebSocket to show real-time updates.

6. **Authentication and Authorization**
   - Secure endpoints using JWT tokens and role-based permissions.
   - Ensure only authorized users can create or manage auctions.

7. **Testing and Validation**
   - Write tests for all API endpoints and WebSocket communication.
   - Validate the user experience through usability testing.

8. **Deployment and Scaling**
   - Deploy on a scalable cloud platform (AWS, GCP, etc.).
   - Use containerization (Docker) for easy deployment and scaling.
   - Implement a load balancer and auto-scaling for handling traffic spikes.

### 5. **Considerations and Future Enhancements**

1. **Scalability**: Design the system to handle multiple concurrent auctions and bids.
2. **Security**: Protect user data and transactions using encryption and secure coding practices.
3. **Payment Integration**: Consider integrating payment gateways for seamless transactions.
4. **Analytics**: Implement tracking for user engagement, auction views, and bid patterns.
5. **User Notifications**: Implement real-time notifications for bid updates, auction reminders, and payment deadlines.

### Summary

The Auction System MVP is designed to provide a seamless and engaging experience for artists and bidders. The architecture focuses on scalability, real-time interaction, and security, ensuring that the platform can grow with its user base. By leveraging FastAPI, PostgreSQL, and Vue.js, you can create a robust and user-friendly auction platform tailored for the art community.
