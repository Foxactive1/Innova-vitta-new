def test_application_factory_registers_auth_security_and_migrations(monkeypatch):
    import importlib

    monkeypatch.setenv("SECRET_KEY", "test-secret-key-that-is-not-used-in-production")
    module = importlib.import_module("app")

    class TestConfig:
        SECRET_KEY = "test-secret-key-that-is-not-used-in-production"
        SQLALCHEMY_DATABASE_URI = "sqlite://"
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        RATELIMIT_STORAGE_URI = "memory://"
        WTF_CSRF_ENABLED = False
        DEBUG = True
        SESSION_COOKIE_SECURE = False

    app = module.create_app(TestConfig)
    assert "auth.login" in app.view_functions
    assert "auth.logout" in app.view_functions
    assert "limiter" in app.extensions
    assert "migrate" in app.extensions
