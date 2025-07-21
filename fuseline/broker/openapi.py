from __future__ import annotations

"""OpenAPI specification for the Fuseline HTTP broker."""

OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Fuseline Broker API", "version": "1.0"},
    "paths": {
        "/worker/register": {
            "post": {
                "summary": "Register worker",
                "requestBody": {
                    "content": {"application/json": {"schema": {"type": "array", "items": {"type": "object"}}}}
                },
                "responses": {"200": {"description": "Worker ID"}},
            }
        },
        "/repository/register": {
            "post": {
                "summary": "Register repository",
                "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                "responses": {"200": {"description": "OK"}},
            }
        },
        "/repository": {
            "get": {
                "summary": "Fetch repository info",
                "parameters": [{"name": "name", "in": "query", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Repository"}, "404": {"description": "Not found"}},
            }
        },
        "/workflow/dispatch": {
            "post": {
                "summary": "Dispatch workflow",
                "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                "responses": {"200": {"description": "Instance ID"}},
            }
        },
        "/workflow/step": {
            "get": {
                "summary": "Get next step",
                "parameters": [{"name": "worker_id", "in": "query", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Step assignment"}, "204": {"description": "No step"}},
            },
            "post": {
                "summary": "Report step result",
                "parameters": [{"name": "worker_id", "in": "query", "required": True, "schema": {"type": "string"}}],
                "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                "responses": {"200": {"description": "OK"}},
            },
        },
        "/worker/keep-alive": {
            "post": {
                "summary": "Keep worker alive",
                "parameters": [{"name": "worker_id", "in": "query", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "OK"}},
            }
        },
        "/openapi.json": {"get": {"summary": "OpenAPI spec", "responses": {"200": {"description": "Specification"}}}},
        "/docs": {"get": {"summary": "Swagger UI", "responses": {"200": {"description": "Swagger UI"}}}},
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
  SwaggerUIBundle({url: '/openapi.json', dom_id: '#swagger-ui'});
  </script>
</body>
</html>"""
