
class TemplateManager():
    # Stores extra templates to display inside another template
    templates = {}

    # Allows module A to add templates to existing templates of module B, without
    # creating a (cyclic) dependency from module B to module A as well
    # (as module B can still function without module A).
    @classmethod
    def set_template(cls, filename, template_name):
        cls.templates[filename] = template_name

    @classmethod
    def get_template(cls, filename):
        if filename in cls.templates:
            return cls.templates[filename]
        return None

