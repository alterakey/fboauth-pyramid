import beaker.session

class _SignedCookie(beaker.session.SignedCookie):
    def __init__(self, secret, **kwargs):
        super(_SignedCookie, self).__init__(bytes(secret, 'UTF-8'), **kwargs)

    def value_decode(self, val):
        return super(_SignedCookie, self).value_decode(self.dumbbytes(val, 'UTF-8'))

    def value_encode(self, val):
        return super(_SignedCookie, self).value_encode(self.dumbbytes(val, 'UTF-8'))

    class dumbbytes(bytes):
        def __init__(self, *args, **kwargs):
            super(_SignedCookie.dumbbytes, self).__init__(*args, **kwargs)

        def strip(self, *args, **kwargs):
            return self
    
def apply():
    beaker.session.SignedCookie = _SignedCookie
