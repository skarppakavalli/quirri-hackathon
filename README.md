backend/
├── agents/
│   ├── __init__.py
│   ├── graph.py
│   ├── nodes.py
│   └── state.py
│
├── tools/
│   ├── student_tools.py
│   ├── teacher_tools.py
│   └── public_tools.py
│
├── services/
│   ├── auth_service.py
│   ├── college_client.py
│   ├── request_service.py
│   └── request_parser.py
│
├── main.py
└── config.py


Student tools
Must-have
- get_attendance
- get_timetable
- get_leave_information
- create_leave_request
- create_od_request

Teacher tools
Must-have
- get_pending_requests
- get_request_details
- approve_request
- reject_request

Public tools
Nice-to-have
- get_college_information
- get_courses
- get_placement_drives
- get_admission_information
- submit_admission_application