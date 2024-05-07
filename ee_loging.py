from google.auth import compute_engine
import ee
credentials = compute_engine.Credentials(scopes=['https://www.googleapis.com/auth/earthengine'])
ee.Initialize(credentials)
