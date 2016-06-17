# -*- coding: utf-8 -*-
#
# Form based authentication for CherryPy. Requires the
# Session tool to be loaded.
#
import sys
import cherrypy
import urllib
import objects
from mako.lookup import TemplateLookup

lookup = TemplateLookup(directories=["./templates/controlcenter"],output_encoding="utf-8",
                        input_encoding="utf-8",encoding_errors="replace")

reload(sys)
sys.setdefaultencoding("utf-8")


SESSION_KEY = '_cp_username'


session_context = {}


def check_credentials(username, password):
    """Verifies credentials for username and password.
    Returns None on success or a string describing the error on failure"""
    # Adapt to your needs
    #if username in ('joe', 'steve') and password == 'secret':
    #    return None
    #else:
    #    return u"Incorrect username or password."
    
    user = objects.get_user_by_login(username)
    user.read()

    if user is None:
        return u"Username %s is unknown to me." % username

    if user.disabled:
        # objects.add_to_log("Пользователь %s отключен." % username, "w")
        return u"User disabled."

    if str(user.password) != str(password):
        # objects.add_to_log("Указан неверный пароль для пользователя %s." % username, "w")
        return u"Incorrect password"
    else:
        return None


    
    # An example implementation which uses an ORM could be:
    # u = User.get(username)
    # if u is None:
    #     return u"Username %s is unknown to me." % username
    # if u.password != md5.new(password).hexdigest():
    #     return u"Incorrect password"


def check_auth(*args, **kwargs):
    """A tool that looks in config for 'auth.require'. If found and it
    is not None, a login is required and the entry is evaluated as a list of
    conditions that the user must fulfill"""
    conditions = cherrypy.request.config.get('auth.require', None)
    # format GET params
    get_parmas = urllib.quote(cherrypy.request.request_line.split()[1])
    if conditions is not None:
        username = cherrypy.session.get(SESSION_KEY)
        if username:
            cherrypy.request.login = username
            for condition in conditions:
                # A condition is just a callable that returns true orfalse
                if not condition():
                    # Send old page as from_page parameter
                    raise cherrypy.HTTPRedirect("/control_center/auth/login?from_page=%s" % get_parmas)
        else: 
            # Send old page as from_page parameter
            raise cherrypy.HTTPRedirect("/control_center/auth/login?from_page=%s" %get_parmas)
            
cherrypy.tools.auth = cherrypy.Tool('before_handler', check_auth)


def require(*conditions):
    """A decorator that appends conditions to the auth.require config
    variable."""
    def decorate(f):
        if not hasattr(f, '_cp_config'):
            f._cp_config = dict()
        if 'auth.require' not in f._cp_config:
            f._cp_config['auth.require'] = []
        f._cp_config['auth.require'].extend(conditions)
        return f
    return decorate

# Conditions are callables that return True
# if the user fulfills the conditions they define, False otherwise
#
# They can access the current username as cherrypy.request.login
#
# Define those at will however suits the application.


def member_of(groupname):
    def check():
        # replace with actual check if <username> is in <groupname>
        user = objects.get_user_by_login(cherrypy.request.login)
        user.read()

        c = False
        if groupname in user.list_access_groups:
            c = True
        return c

    return check


def name_is(reqd_username):
    return lambda: reqd_username == cherrypy.request.login

# These might be handy


def any_of(*conditions):
    """Returns True if any of the conditions match"""
    def check():
        for c in conditions:
            if c():
                return True
        return False
    return check

# By default all conditions are required, but this might still be
# needed if you want to use it inside of an any_of(...) condition


def all_of(*conditions):
    """Returns True if all of the conditions match"""
    def check():
        for c in conditions:
            if not c():
                return False
        return True
    return check


# Controller to provide login and logout actions
class AuthController(object):
    
    def on_login(self, username):
        """Called on successful login"""
        user = objects.get_user_by_login(username)
        cherrypy.session['session_context']["user"] = user
        cherrypy.session['session_context']["category"] = objects.GetCategory()

    def on_logout(self, username):
        """Called on logout"""
    
    def get_loginform(self, username, msg="Enter login information", from_page="/control_center"):
        tmpl = lookup.get_template("auth.html")        
        
        return tmpl.render(username = username, msg=msg, from_page = from_page)
    
    @cherrypy.expose
    def login(self, username=None, password=None, from_page="/control_center"):
        print "Login from_page ", from_page
        if username is None or password is None:
            return self.get_loginform("", from_page=from_page)
        
        error_msg = check_credentials(username, password)
        if error_msg:
            print error_msg
            return self.get_loginform(username, error_msg, from_page)
        else:
            cherrypy.session.regenerate()
            cherrypy.session[SESSION_KEY] = cherrypy.request.login = username
            cherrypy.session['session_context'] = {'login': str(username)}

            self.on_login(username)
            raise cherrypy.HTTPRedirect(from_page or "/control_center")

    @cherrypy.expose
    def logout(self, from_page="/control_center"):
        sess = cherrypy.session
        username = sess.get(SESSION_KEY, None)
        sess[SESSION_KEY] = None
        if username:
            cherrypy.request.login = None
            self.on_logout(username)
        raise cherrypy.HTTPRedirect(from_page or "/control_center")