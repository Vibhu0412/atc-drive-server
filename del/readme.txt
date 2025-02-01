payload for login api :-
{
    "email":"admin@example.com",
    "password":"admin_password"
}

example response of login api :-
{
  "detail": {
    "user": {
      "id": "bf7c909e-6610-4338-95c6-cacb22acf527",
      "username": "admin",
      "email": "admin@example.com",
      "role_id": "a1d14302-756a-44b2-9c95-ba6ef02d9f48",
      "created_at": "2025-01-23T11:44:35.137654Z",
      "last_login": "2025-01-24T08:13:27.255009Z"
    },
    "role": {
      "id": "a1d14302-756a-44b2-9c95-ba6ef02d9f48",
      "name": "admin",
      "can_view": true,
      "can_edit": true,
      "can_delete": true,
      "can_create": true,
      "can_share": true
    },
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTczNzcwODIwN30.cLOJjlVKfihiEb1OmCo4OE64H1e7TvkWlisJa1ufqI8",
    "refresh_token": "2V-NUc8n0ZOYjYNnj1JW7gmGyPpQqjplWYBm8FJHoHo",
    "token_type": "bearer"
  },
  "meta": {
    "message": "Login successful",
    "code": 200
  }
}

--> second api where admin can register new user himself payload example (only admin should be allowed to hit this):-
--> token should be passed in headers > example :- Bearer <token>
--> include it in the Authorization header of HTTP requests when interacting with this api
{
    "username": "admin5",
    "password_hash":"admin4",
    "email": "admin5@example.com",
    "role_id": "a1d14302-756a-44b2-9c95-ba6ef02d9f48"
}