from typing import List
import click
from reportseff.job import Job


class Output_Renderer():
    def __init__(self,
                 valid_titles: List,
                 format_str: str = 'JobID%>,State,Elapsed%>,CPUEff,MemEff'):
        '''
        Initialize renderer with format string and list of valid titles
        '''
        # values always included in output
        self.always_included = [
            'JobID%>',
            'State'
        ]
        # values required for proper parsing, need not be included in output
        self.required = [
            'JobID',
            'JobIDRaw',
            'State'
        ]
        # values derived from other values, list includes all dependent values
        self.derived = {
            'CPUEff': ['TotalCPU', 'AllocCPUS', 'Elapsed'],
            'MemEff': ['REQMEM', 'NNodes', 'AllocCPUS', 'MaxRSS'],
            'TimeEff': ['Elapsed', 'Timelimit']
        }

        # build formatters
        self.formatters = self.build_formatters(format_str)

        # validate with titles and derived keys
        valid_titles += self.derived.keys()
        self.query_columns = self.validate_formatters(valid_titles)

        # make sure always included formatters are in list
        self.add_included()

        # build columns for sacct call
        self.correct_columns()

    def build_formatters(self, format_str: str) -> List:
        '''
        Generate list of formatters from comma separated list in format string
        Return list of formatters
        '''
        return [Column_Formatter(fmt)
                for fmt in format_str.split(',')
                if fmt != '']

    def validate_formatters(self, valid_titles: List) -> List:
        '''
        Validate all titles of formatters
        Return list of query columns
        '''
        return [fmt.validate_title(valid_titles)
                for fmt in self.formatters]

    def add_included(self):
        '''
        If the always included columns are not in formatters, prepend them
        '''
        # reverse so inserted in same order
        for title in reversed(self.always_included):
            # remove any format information when testing membership
            name = title.split('%')[0]
            if name not in self.formatters:
                self.formatters.insert(0, Column_Formatter(title))

    def correct_columns(self):
        '''
        use derived values to update the list of query columns
        '''
        result = [self.derived[c] if c in self.derived else [c]
                  for c in self.query_columns]
        # flatten
        result = [item for sublist in result for item in sublist]

        # add in required values
        result += self.required

        # remove duplicates
        self.query_columns = list(set(result))

    def format_jobs(self, jobs: List[Job]) -> str:
        '''
        Given list of jobs, build output table
        '''
        result = '  '.join([fmt.format_title()
                            for fmt in self.formatters])

        # TODO finish
        return result


class Column_Formatter():
    def __init__(self, token):
        '''
        Build column entry from format string of the form
        NAME[%[ALIGNMENT]WIDTH]
        '''
        tokens = token.split('%')
        self.title = tokens[0]
        self.alignment = '^'
        self.width = None  # must calculate later
        if len(tokens) > 1:
            format_str = tokens[1]
            if format_str[0] in '<^>':
                self.alignment = format_str[0]
                format_str = format_str[1:]
            if format_str:
                try:
                    self.width = int(format_str)
                except ValueError:
                    raise ValueError(f"Unable to parse format token '{token}'")

    def __eq__(self, other):
        if isinstance(other, Column_Formatter):
            return self.__dict__ == other.__dict__
        if isinstance(other, str):
            return self.title == other
        return False

    def __repr__(self):
        return f'{self.title}%{self.alignment}{self.width}'

    def validate_title(self, valid_titles: List) -> str:
        '''
        Tries to find this formatter's title in the valid titles list
        case insensitive.  If found, replace with valid_title to correct
        capitalization to match valid_titles entry.
        If not found, raise value error
        Returns the valid title found
        '''
        fold_title = self.title.casefold()
        for title in valid_titles:
            if fold_title == title.casefold():
                self.title = title
                return title

        raise ValueError(f"'{self.title}' is not a valid title")

    def compute_width(self, entries: List):
        '''
        Determine the max width of all entries if the width attribute is unset.
        Includes title in determination
        '''
        if self.width is not None:
            return

        self.width = len(self.title)
        for entry in entries:
            width = len(entry)
            self.width = self.width if self.width > width else width

    def format_title(self) -> str:
        result = self.format_entry(self.title)
        return click.style(result, bold=True)

    def format_entry(self, entry: str, color: str = None) -> str:
        '''
        Format the entry to match width, alignment, and color request
        If no color is supplied, will just return string
        If supplied, use click.style to change fg
        If the entry is longer than self.width, truncate the end
        '''
        if self.width is None:
            raise ValueError(f'Attempting to format {self.title} '
                             'with unset width!')

        entry = entry[:self.width]
        result = ('{:' + self.alignment + str(self.width) + '}').format(entry)
        if color:
            result = click.style(result, fg=color)
        return result

    '''
    TODO
    constructor should take a list of comma separated values
    each value is a format from `sacct --helpformat` with an optional
    %width value
    use those values to build sacct call, have sacct as member object here
    (make sacct object as queue_inquirer)
    add in custom values cpueff, memeff, timeeff
    default width is 4 + max, centered
    override alignment with < or >
    custom values and defaults I already have can override those
    job update then needs to handle the new dictionary values, use master
    jobid values unless it is unset
    '''
