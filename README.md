# Retrod PMS Backend - Foundation Layer & Authentication System

This is the production-ready backend Foundation Layer for the Retrod SaaS Property Management System (PMS), implemented using **Django 5** and **Django REST Framework (DRF)**.

## Core Features Implemented
* **SaaS Multi-Tenant Architecture**: Subdomain-based tenant resolution middleware (`TenantResolutionMiddleware`) isolating all data layers.
* **Dual-Method User Authentication**:
  * **Password Login**: Complete email/username verification with brute-force protection (5 failed attempts locks accounts for 15 minutes).
  * **OTP Login**: Two-step flow generating secure 6-digit verification codes (5-minute expiration window), dispatched via an abstract `OTPProvider` layer.
* **Role-Based Access Control (RBAC)**: Fine-grained user mapping per property location (`UserPropertyRole`) and decorator gates (`@require_property_access`) checking property-scoped actions.
* **Structured Auditing**: Immutable logging middleware (`AuditMiddleware`) capturing actor states, IP addresses, trace context, and mutations.
* **OpenAPI Documentation**: Interactive Swagger endpoints fully describing the API payload configurations.

---

## Directory Structure
```text
PMSbackend/
├── manage.py
├── requirements.txt
├── db.sqlite3            # SQLite local/test fallback database
├── retrod_pms/
│   ├── settings.py       # Configuration settings
│   ├── urls.py           # Root URL routing
│   └── wsgi.py
└── apps/
    ├── common/           # Reusable BaseModel with soft-deletes and seed tools
    ├── tenants/          # Subdomain middleware and Tenant/Property registers
    ├── rbac/             # Security decorators, roles, and property maps
    ├── accounts/         # AppUser model and auth services (SimpleJWT + OTP providers)
    └── audit/            # Structured AuditLog capture and middleware
```

---

## Setup & Local Execution

### 1. Install Dependencies
Initialize your virtual environment and install the required packages:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Database Migrations
Apply database schemas and initialize relations:
```bash
python manage.py migrate
```

### 3. Seed Mock Database Data
Bootstrap default permissions, roles, properties, and pre-configured accounts:
```bash
python manage.py seed_pms
```
This bootstraps:
* **Tenant**: `grandpalace` (Grand Palace Group)
* **Properties**: Delhi (`The Grand Palace - New Delhi`) & Goa (`The Grand Palace Resort - Goa`)
* **Roles**: `super_admin`, `owner`, `general_manager`, `front_office_manager`, `front_desk_agent`, etc.
* **Users** (Password is set to `Password123` for all seeded accounts):
  * `admin@retrod.in` (Superuser)
  * `aarav@grandpalace.in` (Owner of Grand Palace Delhi)
  * `vikram@grandpalace.in` (GM of Grand Palace Delhi & Goa)
  * `neha@grandpalace.in` (Front Office Manager)
  * `rohan@grandpalace.in` (Front Desk Agent)

### 4. Run Development Server
Start the development server:
```bash
python manage.py runserver
```

---

## API Endpoints List

### Authentication Endpoints
* **`POST /api/auth/login/`**: Password Authentication. Requires `subdomain`, `email_or_username`, and `password`.
* **`POST /api/auth/request-otp/`**: Step 1 OTP Login. Requires `subdomain` and contact email or phone. Dispatches a 6-digit code.
* **`POST /api/auth/verify-otp/`**: Step 2 OTP Login. Validates code and issues access/refresh tokens.
* **`POST /api/auth/refresh/`**: SimpleJWT rotation to get a fresh access token.
* **`POST /api/auth/logout/`**: Blacklists refresh token.
* **`GET /api/auth/me/`**: Profile context, permitted scopes, and authorized properties for the logged-in user.

### Admin CRUD API ViewSets
* `/api/tenants/`
* `/api/properties/`
* `/api/roles/`
* `/api/permissions/`
* `/api/role-permissions/`
* `/api/user-property-roles/`
* `/api/users/`
* `/api/audit-logs/`

---

## Swagger OpenAPI Interactive Docs
When the server is running, load the Swagger UI in your browser to interact with all API scopes:
* **URL**: `http://127.0.0.1:8000/api/schema/swagger-ui/`

---

## Running Automated Tests
Execute the testing suite covering isolation and safety boundaries:
```bash
python manage.py test
```
