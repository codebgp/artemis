from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin, RoleMixin

db = SQLAlchemy()

roles_users = db.Table('roles_users', \
db.Column('user_id', db.Integer(), db.ForeignKey('user.id')), \
db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Role %r>' % (self.name)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    def __init__(self, email, password, active, roles):
        self.email = email
        self.password = password
        self.active = active
        self.roles = roles

    def __repr__(self):
        return '<User %r>' % (self.email)


class Monitor(db.Model):
    __tablename__ = 'monitors'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prefix = db.Column(db.String(44))
    origin_as = db.Column(db.String(6))
    peer_as = db.Column(db.String(6))
    as_path = db.Column(db.String(100))
    service = db.Column(db.String(50))
    type = db.Column(db.String(1))
    communities = db.Column(db.String(100))
    timestamp = db.Column(db.Float)
    hijack_id = db.Column(db.Integer, nullable=True)
    handled = db.Column(db.Boolean)
    matched_prefix = db.Column(db.String(44), nullable=True)

    __table_args__ = (
        db.UniqueConstraint(
            'prefix',
            'origin_as',
            'peer_as',
            'as_path',
            'service',
            'type',
            'communities',
            'timestamp'
        ),
    )

    def __check_as_path(self, as_path):
        res = []
        for as_ in as_path:
            if isinstance(as_, int):
                res.append(str(as_))
            else:
                raise ValueError('Received wrong AS path format')
        return ' '.join(res)


    def __init__(self, msg):
        self.prefix = msg['prefix']
        self.service = msg['service']
        self.type = msg['type']
        if self.type == 'A':
            self.as_path = self.__check_as_path(msg['as_path'])
            self.origin_as = str(msg['as_path'][-1])
            self.peer_as = str(msg['as_path'][0])
            if 'communities' in msg:
                self.communities = str([(c.get('asn', 0),c.get('value', 0)) for c in msg['communities']])
            else:
                self.communities = ''
        else:
            self.as_path = ''
            self.origin_as = ''
            self.peer_as = ''
            self.communities = ''
        self.timestamp = msg['timestamp']
        self.hijack_id = None
        self.handled = False
        self.matched_prefix = None

    def __repr__(self):
        repr_str = '[\n'
        repr_str += '\tTYPE:         {}\n'.format(self.type)
        repr_str += '\tPREFIX:       {}\n'.format(self.prefix)
        repr_str += '\tORIGIN AS:    {}\n'.format(self.origin_as)
        repr_str += '\tPEER AS:      {}\n'.format(self.peer_as)
        repr_str += '\tAS PATH:      {}\n'.format(self.as_path)
        repr_str += '\tSERVICE:      {}\n'.format(self.service)
        repr_str += '\tCOMMUNITIES:  {}\n'.format(self.communities)
        repr_str += '\tTIMESTAMP:    {}\n'.format(self.timestamp)
        repr_str += ']'
        return repr_str

    def __str__(self):
        return '<Monitor {}, {}, {}, {}, {}>'.format(self.type, self.prefix, self.as_path, self.service, self.timestamp)


class Hijack(db.Model):
    __tablename__ = 'hijacks'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type = db.Column(db.String(1))
    prefix = db.Column(db.String(44))
    hijack_as = db.Column(db.String(6))
    num_peers_seen = db.Column(db.Integer)
    num_asns_inf = db.Column(db.Integer)
    time_started = db.Column(db.Float)
    time_last = db.Column(db.Float)
    time_ended = db.Column(db.Float)
    mitigation_started = db.Column(db.Float)
    to_mitigate = db.Column(db.Boolean)

    def __init__(self, msg, asn, htype):
        self.type = htype
        self.prefix = msg.prefix
        self.hijack_as = asn
        self.num_peers_seen = 1
        if htype in {'S','Q'}:
            self.num_asns_inf = len(
                set(msg.as_path.split(' '))) - 1
        else:
            inf_asns_to_ignore = int(htype) + 1
            self.num_asns_inf = len(
                set(msg.as_path.split(' ')[:-inf_asns_to_ignore]))
        self.time_started = msg.timestamp
        self.time_last = msg.timestamp
        self.time_ended = None
        self.mitigation_started = None
        self.to_mitigate = False

    def __repr__(self):
        repr_str = '[\n'
        repr_str += '\tTYPE:         {}\n'.format(self.type)
        repr_str += '\tPREFIX:       {}\n'.format(self.prefix)
        repr_str += '\tHIJACK AS:    {}\n'.format(self.hijack_as)
        repr_str += '\tTIME STARTED: {}\n'.format(self.time_started)
        repr_str += ']'
        return repr_str

    def __str__(self):
        return '<Hijack {}, {}, {}, {}>'.format(self.type, self.prefix, self.hijack_as, self.time_started)

    def to_dict(self):
        return {
            'id': int(self.id),
            'type': str(self.type),
            'prefix': str(self.prefix),
            'hijack_as': str(self.hijack_as),
            'num_peers_seen': int(self.num_peers_seen),
            'num_asns_inf': int(self.num_asns_inf),
            'time_started': float(self.time_started),
            'time_last_updated': float(self.time_last)
        }