import numpy as np
import pandas as pd


class RSpace():
    """A wrapper around `rpy2` package to facilitate import/export of variables between R and Python as well as running R commands.

    Returns:
        RSpace object: An instance of the RSpace wrapper

    Examples:

    """

    from rpy2 import robjects as ro
    from rpy2.robjects import pandas2ri
    import rpy2.rlike.container as rlc

    def __init__(self, ipython=False):
        """Initiates an `R` environment.

        Args:
            ipython (bool, optional): It enables the `%R` magics command. See 
                https://rpy2.github.io/doc/latest/html/interactive.html for details
        """
        self.ro = RSpace.ro
        
        # loads IPython extension: https://rpy2.github.io/doc/latest/html/interactive.html#usage
        if ipython:
            # source: https://stackoverflow.com/questions/10361206/how-to-run-ipython-magic-from-a-script
            from IPython import get_ipython
            ipython_shell = get_ipython()
            ipython_shell.run_line_magic("load_ext", "rpy2.ipython")

    def __setitem__(self, name, value):
        if isinstance(value, (dict, )):
            value = RSpace.rlc.TaggedList(value.values(), tags=value.keys())

        with (RSpace.ro.default_converter + RSpace.pandas2ri.converter).context():
            value_r = RSpace.ro.conversion.get_conversion().py2rpy(value)
            RSpace.ro.r.assign(name, value_r)

    def __getitem__(self, name):
        with (RSpace.ro.default_converter + RSpace.pandas2ri.converter).context():
            value_py = RSpace.ro.conversion.get_conversion().rpy2py(RSpace.ro.globalenv[name])

        # check if the variable is scalar: https://stackoverflow.com/questions/38088392/how-do-you-check-for-a-scalar-in-r
        if self(f'is.atomic({name}) && length({name}) == 1L')[0]:
            return value_py[0]
        
        # check if the variable is already typed properly
        if isinstance(value_py, (pd.DataFrame, )):
            return value_py
        
        # do we have an array of Strings?
        if isinstance(value_py, RSpace.ro.vectors.StrVector):
            return np.array(value_py)
        
        # check if the variable is more than 2D
        if isinstance(value_py, (np.ndarray, )) and value_py.ndim > 2:
            return value_py

        # adding column names if present
        # source: https://stackoverflow.com/questions/12944250/handing-null-return-in-rpy2
        # source: https://stackoverflow.com/questions/73259425/how-to-load-a-rtypes-nilsxp-data-object-when-using-rpy2
        if self(f'dim({name})') == self.ro.rinterface.NULL:
            value_pd = pd.Series(
                data=dict(value_py),
            )
            if self(f'names({name})') != self.ro.rinterface.NULL:
                value_pd.index = list(self(f'names({name})'))
        else:
            value_pd = pd.DataFrame(
                data=value_py,
            )
            if self(f'rownames({name})') != self.ro.rinterface.NULL:
                value_pd.index = self(f'rownames({name})')
            if self(f'colnames({name})') != self.ro.rinterface.NULL:
                value_pd.columns = self(f'colnames({name})')

        return value_pd

    def __call__(self, r_script):
        return self.ro.r(r_script)

    def __repr__(self):
        return f'''
        R space holds {len(self.ro.globalenv)} variables: {list(self.ro.globalenv)}
        '''

    @classmethod
    def obj2cat(cls, dataframe: pd.DataFrame):
        # print(dataframe.dtypes)
        converted = dataframe.copy()
        for col in converted.columns:
            if converted[col].dtype == object:
                converted[col] = converted[col].astype("category")
                # print(f'"{col}" dtype is now =>', data[col].dtype)
        # print(converted.dtypes)
        return converted

    @classmethod
    def as_lines(cls, strings: list):
        return '\n'.join(strings)


if __name__ == '__main__':
    R = RSpace()

    R("""
    data <- read.table(text="
    index expression mouse treat1 treat2
    1 1.01 MOUSE1 NO NO
    2 1.04 MOUSE2 NO NO
    3 1.04 MOUSE3 NO NO
    4 1.99 MOUSE4 YES NO
    5 2.36 MOUSE5 YES NO
    6 2.00 MOUSE6 YES NO
    7 2.89 MOUSE7 NO YES
    8 3.12 MOUSE8 NO YES
    9 2.98 MOUSE9 NO YES
    10 5.00 MOUSE10 YES YES
    11 4.92 MOUSE11 YES YES
    12 4.78 MOUSE12 YES YES", 
    sep=" ", header=T)
    print(data)

    design <- model.matrix(~ treat1 + treat2, data=data)
    fit <- lm(formula='expression ~ treat1 + treat2', data=data)
    model_matrix <- model.matrix(fit)
    model_coef <- coef(fit)
    print(model_coef)
    """)
    print(R['model_matrix'])
    print(R['model_coef'])
