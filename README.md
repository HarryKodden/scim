![CI Workflow](https://github.com/harrykodden/scim-sample/actions/workflows/ci.yml/badge.svg) ![cov](https://raw.githubusercontent.com/HarryKodden/scim-sample/python-coverage-comment-action-data/badge.svg)

# SCIM

## Docker image

Public image available at:
<https://hub.docker.com/r/harrykodden/scim>

You do not need to build the docker image yourself. You can just pull the prepared image which is available for both **linux/amd** and **linux/arm** architectures.

```bash
docker pull harrykodden/scim
```

## Build the image

Alternatively, you can build the image yourself:

```bash
docker build -t scim .
```

## Starting the application

```bash
docker run -p 8000:8000 harrykodden/scim
```

or if you build it yourself:

```bash
docker run -p 8000:8000 scim
```

This will show like:

```log
INFO: Started server process [1]
INFO: Waiting for application startup.
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

go to your browser and open window at:

```bash
http://localhost:8000
```

This will open the OpenAPI document interface. In this you can experiment and execute all the SCIM API Endpoints.

![OpenAPI Document](openapi.png)

## Data handling options

You have different options to handle the data. The simplest is the the flat files handling. You simply assign a (volume-) path to the location where you want to persist the data.
Other options include SQL and NoSQL database, JumpCloud and forwarding the data to an upstream SCIM Server.

![Data Handling Options](data.png)

The options can be activated by assiging environment variable values, see below.

The plugin methodology makes it very easy to add additional data backends, you simply have to subclass the **Plugin Class** (`code/data/plugins/__init__.py`) and provide logic for the base class methods.

```python
# code/data/plugins/__init__.py

from typing import Any
import uuid


class Plugin(object):
    """Base class that each plugin must inherit from. within this class
    you must define the methods that all of your plugins must implement
    """

    def __init__(self):
        self.description = 'UNKNOWN'

    def id(self) -> str:
        return str(uuid.uuid4())

    def __iter__(self) -> Any:
        raise NotImplementedError

    def __delete__(self, id: str) -> None:
        raise NotImplementedError

    def __getitem__(self, id: str) -> Any:
        raise NotImplementedError

    def __setitem__(self, id: str, details: Any) -> None:
        raise NotImplementedError

```

For inspiration on how to do that, please take a look at the provided implementation examples. If you do want to contribute with a nice additional backend, please do not hesitate to submit a Pull Request.

## Available Plugins...

At this moment the following Plugin Options are implementated:

* Flat Files (e.g. /tmp/Users/..., /tmp/Groups/...)
* Relational Database (SQL)
* MongoDB (No-SQL)
* JumpCloud
* SCIM (Proxy incomming SCIM requests to upstream SCIM Server)
* LDAP
* iRODS (Integrated Rule-Oriented Data System)

The actual Plugin is selected by providing the corresponding envrionment variables, see below.

## Environment variables

This image uses environment variables for configuration.

| Available variables | Description | Example | Default |
| ------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| `LOGLEVEL` | The application logging level | ERROR | INFO |
| `API_KEY` | The API key to authenticate with | mysecret | secret |
| `PAGE_SIZE` | The maximum number of resources returned in 1 response. | 10 | 100 |
| `BASE_PATH` | The base path of all API endpoints | /api/v2 | / |
| `SCHEMA_PATH` | File system path name that contains the SCHEMA files, structure should be similare as the schema folder in this repository | /mnt/schemas | code/.. |
| `DATA_PATH` | File system path name | /mnt/scim | /tmp |
| `MONGO_DB` | Mongo connection string | mongodb://user:password@mongo_host | |
| `DATABASE_URL` | SQL Database connection string | postgresql://user:password@postrgres_host:5432/mydb<br />**or**<br /> mysql+pymysql://user:password@mysql_host/mydb | |
| `JUMPCLOUD_URL` | The API endpoint for JumpCloud | <https://console.jumpcloud.com> | |
| `JUMPCLOUD_KEY` | The API Key for your JumpCloud tenant | **value** of API key obtained from JumpCloud\_<br /><br />**Mandatory when JUMPCLOUD_URL is set** | |
| `FORWARD_SCIM_URL` | Forward SCIM request to upstream SCIM server | <https://example.com/v2/api> | |
| `FORWARD_SCIM_KEY` | API KEY for **FORWARD_SCIM_URL** scim server. if not provided, **API_KEY** will be used | my-secret-password | |
| `LDAP_HOSTNAME` | Hostname or IP address of LDAP host | ldap.example.org | |
| `LDAP_BASENAME` | Base name of tree in which the SCIM tree will be created | dc=example,dc=org | dc=example, + LDAP_BASENAME |
| `LDAP_USERNAME` | bind user name | cn=admin,dc=example,dc=org | cn=admin,dc=example,dc=org |
| `LDAP_PASSWORD` | bind password | | |
| `IRODS_HOST` | iRODS server hostname or IP address | irods.example.org | |
| `IRODS_PORT` | iRODS server port | 1247 | 1247 |
| `IRODS_ZONE` | iRODS zone name | tempZone | |
| `IRODS_ADMIN_USERNAME` | iRODS service username for authentication | rods | |
| `IRODS_ADMIN_PASSWORD` | iRODS service password for authentication | | |
| `USER_MAPPING` | A JSON string that specify how attribute values should be mapped to different attributes | '{"userName": "sram_user_extension.eduPersonUniqueId"} | |
| `GROUP_MAPPING` | A JSON string that specify how attribute values should be mapped to different attributes | '{"id": "displanNameuser_extension.eduPersonUniqueId"} | |
| `USER_MODEL_NAME` | User model name | myUsers | Users |
| `GROUP_MODEL_NAME` | Group model name | myGroups | Groups |
| `SET_ISSUER` | JWT `iss` claim for Security Event Tokens (RFC 9967) | `https://scim.example.com` | `scim` |
| `SET_AUDIENCE` | Default JWT `aud` for SET delivery | `https://receiver.example.com` | |
| `SET_PUSH_URL` | RFC 8935 push receiver URL for SET delivery | `https://receiver.example.com/scim/events` | |
| `SET_PUSH_TOKEN` | Bearer token for SET push delivery | | |
| `EVENT_MODE` | Provisioning event payload mode: `notice` or `full` | `notice` | `notice` |
| `ASYNC_REQUEST` | Async SCIM requests (RFC 9967 §2.5.1): `none`, `request`, or `long` — see [Async SCIM requests](#async-scim-requests) | `request` | `none` |


## Handling data

The data that is received by this SCIM server can be handled in different ways. Below is an example on how to pick up specific attributes from the received data.

### Example on MySQL

Suppose you have configured a MySQL database via the SQL Plugin configuration. Then your data will be persisted in 2 MySQL database tables **Users** and **Groups**.
The structure of both tables are alike and have only 2 columnns

| id | details |
| ---------------------------- | -------------------------------------------------------------------- |
| unique uuid of this resource | this is a JSON datatype holding the data attributes of this resource |

For example after a provisiong the data for **Users** contains:

| id | details  |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 613277a6-aa52-440e-b604-9bbd14343558 | {\"userName\": \"hkodden5\", \"active\": true, \"externalId\": \"<44cb3ba1-7a58-49af-961d-9a1253a26181@sram.surf.nl>\", \"name\": {\"familyName\": \"Kodden\", \"givenName\": \"Harry\"}, \"displayName\": \"Harry Kodden\", \"emails\": [{\"primary\": true, \"value\": \"harry.kodden@surf.nl\"}] ...} |

Then you would like to retrieve specific values out of the JSON data.
For example, we want to lookup the userName.

```sql
select id, details->'$.userName' as userName from Users where id = '613277a6-aa52-440e-b604-9bbd14343558';
```

will result in:

| id | userName |
| ------------------------------------ | ---------- |
| 613277a6-aa52-440e-b604-9bbd14343558 | "hkodden5" |

# Security events (RFC 9967)

SCIM resource changes are published as [Security Event Tokens (SETs)](https://www.rfc-editor.org/rfc/rfc9967.html) instead of the legacy AMQP `{operation, resource}` format.

Configure `SET_PUSH_URL` on the server and point your receiver at that endpoint (RFC 8935 push). See `TODO.md` for the full roadmap.

Example SET shape (provisioning delete):

```json
{
  "iss": "https://scim.example.com",
  "iat": 1715000000,
  "jti": "6164f3bbf6ff41a88dc94f18cb0620e8",
  "sub_id": {
    "format": "scim",
    "uri": "/Groups/e3e7f74e-fa90-46c9-995f-567494761128",
    "externalId": "9946ca40-2a53-40a8-bc63-fb0758e716e3@sram.surf.nl"
  },
  "events": {
    "urn:ietf:params:scim:event:prov:delete": {}
  }
}
```

### Async SCIM requests

When `ASYNC_REQUEST` is not `none`, the server can accept mutating operations (POST, PUT, PATCH, DELETE) asynchronously per [RFC 9967 §2.5.1](https://www.rfc-editor.org/rfc/rfc9967.html#section-2.5.1).

| `ASYNC_REQUEST` | Meaning |
| --------------- | ------- |
| `none` | Async disabled; all mutations run synchronously (default). |
| `request` | Async only when the client sends `Prefer: respond-async`. |
| `long` | If the operation does not finish within `wait=N` seconds (from `Prefer: wait=N`), the server switches to async and returns 202. |

`ServiceProviderConfig` exposes the active mode in `securityEvents.asyncRequest` and lists `urn:ietf:params:scim:event:misc:asyncresp` in `eventUris` when async is enabled.

#### Client: start an async mutation

Send the usual SCIM request with an extra header:

```http
POST /Users HTTP/1.1
Content-Type: application/scim+json
Prefer: respond-async
Authorization: Bearer <API_KEY>
```

Optional wait hint (used with `ASYNC_REQUEST=long`):

```http
Prefer: respond-async, wait=5
```

The server responds immediately with **202 Accepted** and an empty body:

| Header | Value |
| ------ | ----- |
| `Set-Txn` | Transaction id (UUID) for this operation |
| `Preference-Applied` | `respond-async` |
| `Location` | URL to fetch the result, e.g. `/Async/{txn}` (prefixed by `BASE_PATH` if set) |

Example:

```http
HTTP/1.1 202 Accepted
Set-Txn: 3bbc08f4-7575-40fc-aa65-5438f91ae866
Preference-Applied: respond-async
Location: /Async/3bbc08f4-7575-40fc-aa65-5438f91ae866
```

The mutation continues in the background. Provisioning SETs (`prov:create`, `prov:patch`, and so on) are still emitted when the operation completes, as for synchronous requests.

#### Client: poll the result

Authenticated GET on the `Location` from the 202 response:

```http
GET /Async/3bbc08f4-7575-40fc-aa65-5438f91ae866 HTTP/1.1
Authorization: Bearer <API_KEY>
```

Response body (SCIM JSON) describes the finished operation:

```json
{
  "method": "POST",
  "status": "201",
  "location": "/Users/7e1bcf2e-8d0e-45e1-8003-0e460350c5e5",
  "response": {
    "id": "7e1bcf2e-8d0e-45e1-8003-0e460350c5e5",
    "userName": "async-user",
    "meta": { "location": "/Users/7e1bcf2e-8d0e-45e1-8003-0e460350c5e5", "resourceType": "User" },
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"]
  }
}
```

On failure, `status` reflects the HTTP status and `response` contains a SCIM error object.

#### Receiver: completion SET (`misc:asyncresp`)

When `SET_PUSH_URL` is configured, a completion SET is pushed with the same `txn` as `Set-Txn`:

```json
{
  "iss": "https://scim.example.com",
  "iat": 1715000000,
  "jti": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "txn": "3bbc08f4-7575-40fc-aa65-5438f91ae866",
  "sub_id": {
    "format": "scim",
    "uri": "/Users"
  },
  "events": {
    "urn:ietf:params:scim:event:misc:asyncresp": {
      "method": "POST",
      "status": "201",
      "location": "/Users/7e1bcf2e-8d0e-45e1-8003-0e460350c5e5",
      "response": { }
    }
  }
}
```

Event subscribers can correlate `txn` with the original 202 response instead of polling `GET /Async/{txn}`.

#### Deployment example

```bash
export ASYNC_REQUEST=request
export SET_PUSH_URL=https://receiver.example.com/scim/events
export SET_ISSUER=https://scim.example.com
```

Without `Prefer: respond-async`, behavior is unchanged (synchronous 201/200/204 responses).

**Note:** Async results are stored in memory per process. For multiple workers or restarts, use the completion SET or add a shared store (not included yet).

## CI/CD

Committing changes to this repository initiates the CI pipeline that will result in a docker image creation and uploading to dockerhub.

For CD the **argo** is supported to automatacally refresh the application in your kubernetes cluster.
Assuming you have **argo** running in your cluster, just apply thius manifest:

```
kubectl apply -f argocd/application.yaml
```

Or without cloning this repository, you can even do:

```
https://raw.githubusercontent.com/HarryKodden/scim/refs/heads/main/argocd/application.yaml
```

## Filter examples

Below are a few practical SCIM filter examples demonstrating complex expressions supported by this project.

- Basic equality with list-subfilter: find users with username `bjensen` and a work email

```text
userName eq "bjensen" and emails[type eq "work"]
```

- Nested sub-attribute lookup: match groups where an extension urn contains a value

```text
urn:mace:surf.nl:sram:scim:extension:Group.urn co "surf_demo:test30"
```

- Bracketed list sub-filter: check items in an array for a sub-attribute match

```text
urn:mace:surf.nl:sram:scim:extension:Group.links[name eq "logo"]
```

- Combined logical operators: OR within a parenthesised list-filter combined with another attribute

```text
(emails[type eq "work"] or emails[type eq "home"]) and active eq true
```

- Presence operator on lists: ensure a resource contains the `members` attribute

```text
members pr
```

These examples match the semantics tested in the project's unit tests (`test/test_filter.py`).
