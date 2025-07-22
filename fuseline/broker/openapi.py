from __future__ import annotations

"""OpenAPI specification for the Fuseline HTTP broker."""

OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Fuseline Broker API", "version": "1.0"},
    "tags": [
        {"name": "repository", "description": "Manage workflow repositories"},
        {"name": "worker", "description": "Register and monitor workers"},
        {"name": "workflow", "description": "Dispatch and run workflows"},
        {"name": "system", "description": "Broker metadata"},
    ],
    "paths": {
        "/worker/register": {
            "post": {
                "summary": "Register worker",
                "tags": ["worker"],
                "requestBody": {
                    "content": {"application/json": {"schema": {"type": "array", "items": {"type": "object"}}}}
                },
                "responses": {"200": {"description": "Worker ID"}},
            }
        },
        "/repository/register": {
            "post": {
                "summary": "Register repository",
                "tags": ["repository"],
                "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                "responses": {"200": {"description": "OK"}},
            }
        },
        "/repository": {
            "get": {
                "summary": "Fetch repository info",
                "tags": ["repository"],
                "parameters": [{"name": "name", "in": "query", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Repository"}, "404": {"description": "Not found"}},
            }
        },
        "/workflow/dispatch": {
            "post": {
                "summary": "Dispatch workflow",
                "tags": ["workflow"],
                "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                "responses": {"200": {"description": "Instance ID"}},
            }
        },
        "/workflow/step": {
            "get": {
                "summary": "Get next step",
                "tags": ["workflow"],
                "parameters": [{"name": "worker_id", "in": "query", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Step assignment"}, "204": {"description": "No step"}},
            },
            "post": {
                "summary": "Report step result",
                "tags": ["workflow"],
                "parameters": [{"name": "worker_id", "in": "query", "required": True, "schema": {"type": "string"}}],
                "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                "responses": {"200": {"description": "OK"}},
            },
        },
        "/worker/keep-alive": {
            "post": {
                "summary": "Keep worker alive",
                "tags": ["worker"],
                "parameters": [{"name": "worker_id", "in": "query", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "OK"}},
            }
        },
        "/status": {
            "get": {
                "summary": "Broker status",
                "tags": ["system"],
                "responses": {"200": {"description": "OK"}},
            }
        },
        "/workers": {
            "get": {
                "summary": "List workers",
                "tags": ["worker"],
                "responses": {
                    "200": {
                        "description": "Workers",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/WorkerInfo"},
                                }
                            }
                        },
                    }
                },
            }
        },
    },
    "components": {
        "schemas": {
            "LastTask": {
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"},
                    "instance_id": {"type": "string"},
                    "step_name": {"type": "string"},
                    "success": {"type": "boolean"},
                },
            },
            "WorkerInfo": {
                "type": "object",
                "properties": {
                    "worker_id": {"type": "string"},
                    "connected_at": {"type": "number"},
                    "last_seen": {"type": "number"},
                    "last_task": {"$ref": "#/components/schemas/LastTask"},
                },
                "required": ["worker_id", "connected_at", "last_seen"],
            },
        }
    },
}

SWAGGER_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Fuseline Broker API</title>
  <link rel=\"stylesheet\" href=\"https://unpkg.com/swagger-ui-dist/swagger-ui.css\">
</head>
<body>
  <div id=\"swagger-ui\"></div>
  <script src=\"https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js\"></script>
  <script>
  SwaggerUIBundle({
    url: '/openapi.json',
    dom_id: '#swagger-ui',
    operationsSorter: 'alpha',
    tagsSorter: 'alpha'
  });
  </script>
</body>
</html>"""
