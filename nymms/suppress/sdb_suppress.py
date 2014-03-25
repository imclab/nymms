import logging
import traceback
import time
import uuid
from nymms.suppress.suppress import SuppressFilterBackend, ReactorSuppress

logger = logging.getLogger(__name__)


class SDBSuppressFilterBackend(SuppressFilterBackend):
    def __init__(self, conn, timeout=60, domain_name='reactor_suppress'):
        self._conn = conn
        self._domain_name = domain_name
        self.domain = None
        logger.debug("%s initialized.", self.__class__.__name__)
        super(SDBSuppressFilterBackend, self).__init__(timeout)

    def _setup_domain(self):
        if self.domain:
            return
        logger.debug("setting up reactor suppression domain %s",
                self._domain_name)
        self.domain = self._conn.create_domain(self._domain_name)

    def add_suppression(self, regex, expires, comment, userid, ipaddr):
        """Adds a suppression filter to the SDB store

        regex = regex to match against the NYMMS event key
        expire = number of seconds this filter should be active
        comment = Why you added this filter
        userid = userid of user creating this filter
        ipaddr = IP address of host creating this filter
        """
        self._setup_domain()
        rowkey = uuid.uuid4()
        if self.domain.put_attributes(rowkey,
                {
                    'regex': regex,
                    'created_at': int(time.time()),
                    'expires': expires,
                    'comment': comment,
                    'userid': userid,
                    'ipaddr': ipaddr,
                    'rowkey': rowkey,
                    'active': 'True'
                }):
            logger.debug("Added %s to %s" % (rowkey, self._domain_name))
            return rowkey
        else:
            return False

    def get_suppressions(self, expire, active=True):
        """Returns a list of suppression filters which were active between start and end
        expire = expoch time
        active = True/False to limit to only filters flagged 'active' = 'True'
        """
        self._setup_domain()
        if expire:
            query = "select * from `%s` where `expires` >= '%s'" % (
                    self._domain_name, expire)
        else:
            query = "select * from `%s` where `expires` > '0'" % (
                    self._domain_name,)

        if active:
            query += " and `active` = 'True'"
        query += " order by expires"

        filters = []
        for item in self.domain.select(query):
            filters.append(ReactorSuppress(item))

        return filters

    def deactivate_suppression(self, rowkey):
        """Deactivates a single suppression filter"""
        self._setup_domain()
        self._conn.put_attributes(self._domain_name, rowkey,
                {'active': int(time.time())})
