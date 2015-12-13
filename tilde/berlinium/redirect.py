
# inject custom welcome page for browser

from sockjs.tornado.static import GreetingsHandler

def add_redirection(router_urls, destination):
    if not destination.startswith('http'): raise RuntimeError("Wrong redirection destination URL!")

    class RedirectHandler(GreetingsHandler):
        def initialize(self, server):
            self.server = server

        def get(self):
            self.redirect(destination)

    for n, i in enumerate(router_urls):
        if i[0].endswith('/?'):
            router_urls[n] = (i[0], RedirectHandler, i[2])

    return router_urls
