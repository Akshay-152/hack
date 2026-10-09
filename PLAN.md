# Campus Event Recommendation Bot --- Project Plan

## 1. Project Overview

**Project name:** Campus Event Recommendation Bot\
**Domain:** Student Engagement

Build a web-based bot that recommends college events to students based
on their interests, academic year, department, and event availability.
The goal is to help students discover relevant campus activities and
improve participation.

## 2. Problem Statement

Students may miss useful campus events because announcements are spread
across notice boards, class groups, social media, and college websites.
A central recommendation bot can collect event information and suggest
suitable events to each student.

## 3. Objectives

-   Let students select and update their interests.
-   Store campus events in a searchable database.
-   Recommend events that match a student's interests.
-   Display event dates, times, venues, descriptions, and registration
    links.
-   Allow students to save events and register.
-   Provide an admin interface for publishing and updating events.
-   Send reminders for upcoming events, where notification support is
    available.

## 4. Target Users

### Students

-   Create or update a profile.
-   Select interests such as coding, AI, sports, music, arts,
    entrepreneurship, and volunteering.
-   Browse recommended and upcoming events.
-   Save events and register.

### Event Administrators

-   Add, edit, publish, or cancel events.
-   Set event category, date, venue, capacity, and registration details.
-   View registrations and basic engagement statistics.

## 5. Recommended Technology Stack

  -----------------------------------------------------------------------
  Layer                   Technology              Purpose
  ----------------------- ----------------------- -----------------------
  Frontend                HTML, CSS, JavaScript   Student and admin
                                                  interfaces

  Backend                 Python Flask            API endpoints and
                                                  application logic

  Database                Firebase Firestore      Profiles, events,
                                                  registrations, and
                                                  saved events

  Authentication          Firebase Authentication Student and admin
                                                  sign-in

  Recommendation engine   Python                  Match interests to
                                                  events

  Hosting                 Firebase Hosting or     Publish the web
                          another suitable host   application

  Version control         Git and GitHub          Source code and
                                                  collaboration
  -----------------------------------------------------------------------

**MVP choice:** Start with HTML, CSS, JavaScript, Flask, and Firebase.
Avoid adding complex AI until the basic recommendation flow works.

## 6. Core Features

### 6.1 Student Profile

Store a user ID, name, department, year/semester, and selected
interests. Collect only the information needed by the application.

### 6.2 Event Management

Each event should include: - Event ID - Title and description - Category
and tags - Date and start/end time - Venue or online meeting link -
Organizer - Registration deadline and capacity - Status: draft,
published, or cancelled - Optional registration URL

### 6.3 Personalized Recommendations

For the first version, use transparent rule-based matching: 1. Compare a
student's interests with the event's category and tags. 2. Give higher
priority to events matching multiple interests. 3. Exclude cancelled and
past events. 4. Prioritize events with registration still open. 5. Sort
by match score and then by date.

Example scoring rule: - Category match: +3 points - Each matching tag:
+2 points - Department or year relevance: +1 point, if the event
specifies a target group - Past or cancelled event: exclude it

This is a simple starting rule and can be tuned after testing.

### 6.4 Event Discovery

Provide filters for category, date, department, and keyword. Include a
page for all upcoming events as well as personalized recommendations.

### 6.5 Save and Register

Students can bookmark events and register. Prevent duplicate
registrations and enforce event capacity on the backend.

### 6.6 Notifications

Add in-app reminders first. Email or push notifications can be
introduced later, with user consent and appropriate configuration.

### 6.7 Admin Dashboard

Require admin authentication. Only authorized admins can create, edit,
publish, cancel, or manage events.

## 7. Database Design

Suggested Firestore collections:

### `users`

-   `uid`
-   `name`
-   `department`
-   `year`
-   `interests` --- array of strings
-   `createdAt`

### `events`

-   `eventId`
-   `title`
-   `description`
-   `category`
-   `tags` --- array of strings
-   `date`
-   `startTime`
-   `endTime`
-   `venue`
-   `organizer`
-   `registrationDeadline`
-   `capacity`
-   `status`
-   `createdBy`
-   `createdAt`

### `registrations`

-   `registrationId`
-   `eventId`
-   `uid`
-   `registeredAt`
-   `status`

Use a unique combination of `eventId` and `uid` to prevent duplicate
registrations. Enforce access permissions with Firebase Security Rules
and validate all inputs on the server.

Optional later collections: `savedEvents` and `notifications`.

## 8. Application Flow

1.  Student opens the website.
2.  Student signs in.
3.  Student chooses interests and saves their profile.
4.  Backend retrieves published upcoming events.
5.  Recommendation logic scores each event against the student's
    interests.
6.  Website displays ranked recommendations.
7.  Student opens an event, saves it, or registers.
8.  Admin updates event details through the dashboard.

## 9. API Plan

Suggested Flask endpoints:

  ---------------------------------------------------------------------------------------
  Method                  Endpoint                                Purpose
  ----------------------- --------------------------------------- -----------------------
  `GET`                   `/api/events`                           List published upcoming
                                                                  events

  `GET`                   `/api/events/<event_id>`                Get event details

  `GET`                   `/api/recommendations`                  Get recommendations for
                                                                  the signed-in student

  `PUT`                   `/api/profile/interests`                Update student
                                                                  interests

  `POST`                  `/api/events/<event_id>/register`       Register for an event

  `GET`                   `/api/my-registrations`                 List the student's
                                                                  registrations

  `POST`                  `/api/admin/events`                     Create an event; admin
                                                                  only

  `PUT`                   `/api/admin/events/<event_id>`          Update an event; admin
                                                                  only

  `POST`                  `/api/admin/events/<event_id>/cancel`   Cancel an event; admin
                                                                  only
  ---------------------------------------------------------------------------------------

Require authentication where appropriate. Check authorization on the
backend rather than relying on frontend visibility.

## 10. User Interface Pages

1.  **Landing page:** Project introduction and sign-in.
2.  **Student dashboard:** Recommended events and upcoming events.
3.  **Interests page:** Select and edit interests.
4.  **Event details page:** Description, schedule, venue, and
    registration.
5.  **My events page:** Saved events and registrations.
6.  **Admin dashboard:** Create and manage events.
7.  **Login/profile page:** Authentication and profile settings.

Design the interface to work on mobile phones and desktop screens.

## 11. Development Phases

### Phase 1 --- Requirements and Setup

-   Confirm the minimum feature set.
-   Create a GitHub repository.
-   Set up the frontend and Flask backend.
-   Create a Firebase project and configure authentication and
    Firestore.

### Phase 2 --- Database and Authentication

-   Define collections and access rules.
-   Implement student sign-in.
-   Add student profile and interest selection.
-   Add admin authorization.

### Phase 3 --- Event Management

-   Build event listing and details pages.
-   Implement admin event creation and editing.
-   Add event status and date validation.

### Phase 4 --- Recommendation Engine

-   Implement interest matching and scoring.
-   Exclude past and cancelled events.
-   Sort recommendations by relevance and date.
-   Add category and date filters.

### Phase 5 --- Registration and Saved Events

-   Implement registration and cancellation rules.
-   Prevent duplicate registrations.
-   Enforce capacity and registration deadlines.
-   Build the student's event list.

### Phase 6 --- Testing and Deployment

-   Test authentication, permissions, recommendations, and
    registrations.
-   Test mobile layout and error states.
-   Configure production environment variables and security rules.
-   Deploy the frontend and backend.
-   Collect feedback from a small group of students.

## 12. Testing Checklist

-   [ ] A student can sign in and update interests.
-   [ ] An admin can publish, edit, and cancel an event.
-   [ ] Recommendations match the selected interests.
-   [ ] Past and cancelled events are not recommended.
-   [ ] Students cannot register twice for the same event.
-   [ ] Registration deadlines and capacity are enforced.
-   [ ] Students cannot access admin operations.
-   [ ] Invalid input and network errors are handled.
-   [ ] Firebase rules prevent unauthorized data access.
-   [ ] The application works on mobile and desktop.

## 13. Security and Privacy

-   Keep private keys and server credentials out of frontend code and
    GitHub.
-   Use environment variables for backend secrets.
-   Verify Firebase authentication tokens on the backend.
-   Enforce role-based access control and Firestore Security Rules.
-   Validate input and check event capacity on the server.
-   Collect only necessary student information.
-   Do not expose student registration lists to unauthorized users.

## 14. Future Enhancements

After the MVP works reliably, consider: - A natural-language chatbot
interface. - Semantic recommendations using embeddings. - Calendar
integration and downloadable calendar files. - Email or push
reminders. - Attendance tracking and feedback forms. - Analytics for
event views, registrations, and participation. - Recommendations based
on saved events and explicit feedback.

## 15. Definition of Done

The first version is complete when students can sign in, select
interests, receive relevant upcoming event recommendations, view event
details, and register; admins can securely manage events; and the core
flows pass the testing checklist.

## 16. Suggested Repository Structure

``` text
campus-event-recommendation-bot/
├── frontend/
│   ├── index.html
│   ├── events.html
│   ├── profile.html
│   ├── admin.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js
│       ├── auth.js
│       └── events.js
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── routes/
│   │   ├── events.py
│   │   ├── recommendations.py
│   │   ├── registrations.py
│   │   └── admin.py
│   ├── services/
│   │   └── recommender.py
│   └── requirements.txt
├── tests/
├── .env.example
├── .gitignore
├── README.md
└── PLAN.md
```

Keep real credentials in a local `.env` file or an appropriate secret
manager. Commit `.env.example`, not `.env`.
