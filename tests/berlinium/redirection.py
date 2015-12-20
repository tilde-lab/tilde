
import httplib2
import set_path
from tilde.core.settings import settings

h = httplib2.Http()
h.follow_redirects = False
resp, content = h.request('http://localhost:%s/' % settings['webport'], "GET")
print resp.status
print resp.get('location')
