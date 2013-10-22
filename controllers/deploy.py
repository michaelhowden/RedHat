# -*- coding: utf-8 -*-

"""
    Deployments
"""

module = request.controller
resourcename = request.function

if not settings.has_module(module):
    raise HTTP(404, body="Module disabled: %s" % module)

s3db.hrm_vars()

# =============================================================================
def index():
    """ Module's Home Page """

    module_name = settings.modules[module].name_nice
    response.title = module_name
    return dict(module_name=module_name)
    
# =============================================================================
def deployment():
    """ RESTful CRUD Controller """

    def prep(r):
        created_on = r.table.created_on
        created_on.readable = True
        created_on.label = T("Date Created")
        created_on.represent = lambda d: \
                               s3base.S3DateTime.date_represent(d, utc=True)
        if r.id:
            tablename = r.tablename if not r.component else r.component.tablename
            if r.component_name == "alert":
                # Open up the Select page
                # @ToDo: Integrate this into main page
                # Widget? Custom Create method?
                s3db.configure(tablename,
                               create_next=URL(f="alert",
                                               args=["[id]", "select"]),
                               )
            else:
                next_url = r.url(component="", method="profile")
                s3db.configure(tablename, create_next=next_url)
                s3.cancel = next_url
        else:
            s3.cancel = r.url(method="summary", component=None, id=0)
        return True
    s3.prep = prep

    def postp(r, output):
        s3_action_buttons(r,
                          editable=True,
                          deletable=True,
                          read_url=r.url(method="profile", id="[id]"),
                          update_url=r.url(method="profile", id="[id]"),
                          delete_url=r.url(method="delete", id="[id]"),
                          )
        if isinstance(output, dict) and "buttons" in output:
            # Override standard "List" button
            buttons = output["buttons"]
            if "list_btn" in buttons and "summary_btn" in buttons:
                buttons["list_btn"] = buttons["summary_btn"]
        return output
    s3.postp = postp

    return s3_rest_controller(hide_filter=False)
            
# =============================================================================
def human_resource_assignment():
    """ RESTful CRUD Controller """

    def prep(r):
        if r.representation == "popup":
            r.resource.configure(insertable=False)
        return True
    s3.prep = prep

    return s3_rest_controller()
    
# =============================================================================
def alert():
    """ RESTful CRUD Controller """

    def prep(r):
        if r.component:
            if r.component_name == "response":
                s3db.configure(r.component.tablename,
                               deletable = False,
                               editable = False,
                               insertable = False,
                               )
        else:
            if r.record:
                if r.record.message_id:
                    # Already sent - so lock
                    s3db.configure(r.tablename,
                                   deletable = False,
                                   editable = False,
                                   )
            else:
                s3db.configure(r.tablename,
                               deletable = False,
                               # @ToDo: restrict in postp to change this action button
                               #editable = False,
                               )

            # Hide label for single field in InlineComponent
            #s3db.deploy_alert_recipient.human_resource_id.label = ""
            created_on = r.table.created_on
            created_on.readable = True
            created_on.label = T("Date Created")
            created_on.represent = lambda d: \
                                   s3base.S3DateTime.date_represent(d, utc=True)
        return True
    s3.prep = prep

    def postp(r, output):
        if r.component:
            if r.component_name == "recipient":
                # Open should open the Member, not the Link
                # Delete should remove the Link, not the Member
                s3.actions = [dict(label=str(READ),
                                   _class="action-btn read",
                                   url=URL(f="person",
                                           vars={"human_resource.id":"[id]"})),
                              dict(label=str(DELETE),
                                   _class="delete-btn",
                                   url=URL(f="alert",
                                           args=[r.id, "recipient", "[id]", "delete"])),
                              ]
        else:
            # Delete should only be possible if the Alert hasn't yet been sent
            table = r.table
            query = (table.message_id == None)
            rows = db(query).select(table.id)
            restrict = [str(row.id) for row in rows]
            s3.actions = [dict(label=str(READ),
                               _class="action-btn read",
                               url=URL(f="alert", args="[id]")),
                          dict(label=str(DELETE),
                               _class="delete-btn",
                               restrict=restrict,
                               url=URL(f="alert",
                                       args=[r.id, "delete"])),
                          ]
        return output
    s3.postp = postp

    return s3_rest_controller(rheader=s3db.deploy_rheader)

# =============================================================================
def human_resource():
    """
        'Members' RESTful CRUD Controller
    """

    # Tweak settings for RDRT
    settings.hrm.staff_experience = True
    settings.hrm.use_skills = True
    settings.search.filter_manager = True

    return s3db.hrm_human_resource_controller()
    
# =============================================================================
def person():
    """
        'Members' RESTful CRUD Controller
    """

    # Tweak settings for RDRT
    settings.hrm.staff_experience = "experience"
    settings.hrm.vol_experience = "experience"
    settings.hrm.use_skills = True
    settings.search.filter_manager = True

    return s3db.hrm_person_controller()
    
# -----------------------------------------------------------------------------
def email_inbox():
    """
        RESTful CRUD controller for the Email Inbox
        - all Inbound Email Messages are visible here

        @ToDo: Filter to those which have been unable to be automatically
               processed as being responses to Alerts
        @ToDo: Filter to those coming into the specific account used for
               Deployments
        @ToDo: Provide a mechanism (Action button?) to link a mail manually to
               an Alert
    """

    if not auth.s3_logged_in():
        session.error = T("Requires Login!")
        redirect(URL(c="default", f="user", args="login"))

    tablename = "msg_email"
    table = s3db.msg_email
    s3.filter = (table.inbound == True)
    table.inbound.readable = False

    # CRUD Strings
    s3.crud_strings[tablename] = Storage(
        title_list = T("View InBox"),
        title_update = T("Edit Message"),
        label_list_button = T("View InBox"),
        label_delete_button = T("Delete Message"),
        msg_record_modified = T("Message updated"),
        msg_record_deleted = T("Message deleted"),
        msg_list_empty = T("No Messages currently in InBox")
    )

    s3db.configure(tablename,
                   insertable=False,
                   editable=False)

    return s3_rest_controller("msg", "email")

# END =========================================================================