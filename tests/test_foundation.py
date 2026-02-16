"""Smoke tests for the foundation modules (app factory, utils, log, db)."""

import json

import pytest


class TestAppFactory:
    """Tests for mealbot.app.create_app."""

    def test_create_app_returns_flask_instance(self):
        from mealbot.app import create_app
        app = create_app(testing=True)
        assert app is not None
        assert app.config["TESTING"] is True

    def test_root_route_serves_static(self):
        from mealbot.app import create_app
        app = create_app(testing=True)
        with app.test_client() as client:
            resp = client.get("/privacy.html")
            assert resp.status_code == 200
            assert b"Privacy Policy" in resp.data

    def test_static_sample_csv(self):
        from mealbot.app import create_app
        app = create_app(testing=True)
        with app.test_client() as client:
            resp = client.get("/sample.csv")
            assert resp.status_code == 200


class TestResponseHelpers:
    """Tests for mealbot.utils response helpers."""

    def test_str_to_bytes_format(self):
        from mealbot.utils import str_to_bytes
        result = json.loads(str_to_bytes("hello"))
        assert result == {"Message": "hello"}

    def test_err_to_bytes_format(self):
        from mealbot.utils import err_to_bytes
        result = json.loads(err_to_bytes(Exception("fail")))
        assert result == {"Message": "fail"}

    def test_message_key_is_capitalized(self):
        from mealbot.utils import str_to_bytes
        result = json.loads(str_to_bytes("test"))
        assert "Message" in result
        assert "message" not in result


class TestQueryParamHelpers:
    """Tests for mealbot.utils query parameter helpers."""

    def test_get_query_param_success(self):
        from mealbot.app import create_app
        from mealbot.utils import get_query_param
        app = create_app(testing=True)
        with app.test_request_context("/?org=ysc"):
            assert get_query_param("org") == "ysc"

    def test_get_query_param_missing_raises(self):
        from mealbot.app import create_app
        from mealbot.utils import get_query_param
        app = create_app(testing=True)
        with app.test_request_context("/"):
            with pytest.raises(ValueError, match="must contain missing"):
                get_query_param("missing")

    def test_get_query_params_success(self):
        from mealbot.app import create_app
        from mealbot.utils import get_query_params
        app = create_app(testing=True)
        with app.test_request_context("/?org=ysc&round=1"):
            assert get_query_params(["org", "round"]) == ["ysc", "1"]

    def test_get_query_params_missing_raises(self):
        from mealbot.app import create_app
        from mealbot.utils import get_query_params
        app = create_app(testing=True)
        with app.test_request_context("/?org=ysc"):
            with pytest.raises(ValueError, match="does not contain round"):
                get_query_params(["org", "round"])


class TestLoggingUtilities:
    """Tests for mealbot.log logging utilities."""

    def test_log_and_write_err_returns_response(self):
        from mealbot.app import create_app
        from mealbot.log import log_and_write_err
        app = create_app(testing=True)
        with app.test_request_context("/"):
            resp = log_and_write_err(Exception("db error"), 500, "getOrgs")
            assert resp.status_code == 500
            body = json.loads(resp.data)
            assert body == {"Message": "db error"}

    def test_log_and_write_returns_response(self):
        from mealbot.app import create_app
        from mealbot.log import log_and_write
        app = create_app(testing=True)
        with app.test_request_context("/"):
            resp = log_and_write(json.dumps({"data": "ok"}), 200, "handler")
            assert resp.status_code == 200

    def test_log_and_write_status_bad_request(self):
        from mealbot.app import create_app
        from mealbot.log import log_and_write_status_bad_request
        app = create_app(testing=True)
        with app.test_request_context("/"):
            resp = log_and_write_status_bad_request(Exception("bad"), "handler")
            assert resp.status_code == 400

    def test_log_and_write_status_internal_server_error(self):
        from mealbot.app import create_app
        from mealbot.log import log_and_write_status_internal_server_error
        app = create_app(testing=True)
        with app.test_request_context("/"):
            resp = log_and_write_status_internal_server_error(Exception("crash"), "handler")
            assert resp.status_code == 500


class TestDbModule:
    """Tests for mealbot.db module."""

    def test_duplicate_key_err_constant(self):
        from mealbot.db import DUPLICATE_KEY_ERR
        assert DUPLICATE_KEY_ERR == "duplicate key value violates unique constraint"

    def test_get_db_connection_is_callable(self):
        from mealbot.db import get_db_connection
        assert callable(get_db_connection)
