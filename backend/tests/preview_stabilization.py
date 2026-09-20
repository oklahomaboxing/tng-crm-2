"""Local browser QA with synthetic data only; never imports the production .env."""
import os
from test_stabilization import StabilizationTests, app, engine, TEMP, ORIGINAL_CWD
from app.auth import hash_password
import uvicorn

fixture = StabilizationTests()
fixture.setUp()
for user in fixture.users.values():
    user.password_hash = hash_password("LocalPreview123!")
fixture.db.commit()
os.environ["CLOVER_API_TOKEN"] = ""
os.environ["CLOVER_ECOMMERCE_PRIVATE_KEY"] = ""
try:
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
finally:
    fixture.tearDown()
    engine.dispose()
    os.chdir(ORIGINAL_CWD)
    TEMP.cleanup()
