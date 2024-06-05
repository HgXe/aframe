import numpy as np
import csdl_alpha as csdl
from csdl_alpha.utils.typing import VariableLike
from typing import Union

import numpy as np
import xml.etree.ElementTree as ET
import sys


class Material():
    def __init__(self, name:str=None, density:VariableLike=None, 
                 compliance:VariableLike=None,
                 strength:VariableLike=None):
        """Initialize a Material object.

        Parameters
        ----------
        name : str, optional
            The name of the material. Defaults to None.
        density : VariableLike, optional
            The density of the material. Defaults to None.
        compliance : VariableLike, optional
            The compliance matrix of the material. Defaults to None.
        strength : VariableLike, optional
            The strength matrix of the material. Defaults to None.
        """
        self.name = name
        self.density = density
        self.compliance = compliance
        self.strength = strength
        
    # https://docs.python.org/3/library/xml.etree.elementtree.html
    def import_xml(self, fname:str):
        """Import material properties from an XML file.

        Parameters
        ----------
        fname : str
            The name of the file to import from.
        """
        tree = ET.parse(fname)
        root = tree.getroot()

        self.name = root.attrib['name']

        if root.find('density') is not None: 
            self.density = float(root.find('density').text)
            
        if root.find('compliance') is not None:
            self.compliance = np.array(
                [[float(x) for x in i.text.split()] 
                for i in root.find('compliance')]
                )

        if root.find('strength') is not None:
            self.strength = np.array(
                [[float(x) for x in i.text.split()] 
                for i in root.find('strength')]
                )

    def export_xml(self, fname):
        """Export material properties to an XML file.

        Parameters
        ----------
        fname : str
            The name of the file to export to.
        """
        root = ET.Element('material')
        root.set('type', self.__class__.__name__)
        root.set('name', self.name)

        if self.density is not None:
            ET.SubElement(root, 'density').text = str(self.density)

        if self.compliance is not None:
            compliance_el = ET.SubElement(root, 'compliance')
            for row in self.compliance:
                ET.SubElement(compliance_el, 'row').text = ' '.join(map(str, row))

        if self.strength is not None:
            strength_el = ET.SubElement(root, 'strength')
            for row in self.strength:
                ET.SubElement(strength_el, 'row').text = ' '.join(map(str, row))

        tree = ET.ElementTree(root)
        if sys.version_info[1] >= 9:
            ET.indent(tree) # makes it pretty, new for Python3.9
        tree.write(fname)

class IsotropicMaterial(Material):
    def __init__(self, name:str=None, density:VariableLike=None,
                 E:VariableLike=None, nu:VariableLike=None, G:VariableLike=None,
                 Ft:VariableLike=None, Fc:VariableLike=None, F12:VariableLike=None):
        """Initialize an isotropic material object.

        Parameters
        ----------
        name : str, optional
            The name of the material. Defaults to None.
        density : VariableLike, optional
            The density of the material. Defaults to None.
        E : VariableLike, optional
            The Young's modulus of the material. Defaults to None.
        nu : VariableLike, optional
            The Poisson's ratio of the material. Defaults to None.
        G : VariableLike, optional
            The shear modulus of the material. Defaults to None.
        Ft : VariableLike, optional
            The tensile strength of the material. Defaults to None.
        Fc : VariableLike, optional
            The compressive strength of the material. Defaults to None.
        F12 : VariableLike, optional
            The shear strength of the material. Defaults to None.
        """
        super().__init__(name=name, density=density)

        if E is None and nu is None and G is None:
            pass
        else:
            self.set_compliance(E=E, nu=nu, G=G)
        if Ft is None and Fc is None and F12 is None:
            pass
        else:
            if Ft is None or Fc is None or F12 is None:
                raise Exception('Material strength properties are underdefined')
            self.set_strength(Ft=Ft, Fc=Fc, F12=F12)


    def set_compliance(self, E = None, nu = None, G = None):
            if not None in [E, nu]:
                pass
            elif not None in [G, nu]:
                E = G*2*(1+nu)
            elif not None in [E, G]:
                nu = E/(2*G)-1
            else:
                raise Exception('Material properties are underdefined')

            self.compliance = 1/E*np.array(
                [[1, -nu, -nu, 0, 0, 0],
                [-nu, 1, -nu, 0, 0, 0],
                [-nu, -nu, 1, 0, 0, 0],
                [0, 0, 0, 1+nu, 0, 0],
                [0, 0, 0, 0, 1+nu, 0],
                [0, 0, 0, 0, 0, 1+nu]]
            )

    def from_compliance(self):
        E = 1/self.compliance[0,0]
        nu = -self.compliance[0,1]*E
        G = E/(2*(1+nu))
        return E, nu, G

    def set_strength(self, Ft, Fc, F12):
        self.strength = np.array([[Ft, Ft, Ft],[Fc, Fc, Fc],[F12, F12, F12]])

class TransverseMaterial(Material):
    def __init__(self, name:str=None, density:VariableLike=None,
                EA:VariableLike=None, ET:VariableLike=None, vA:VariableLike=None, vT:VariableLike=None, GA:VariableLike=None,
                F1t:VariableLike=None, F1c:VariableLike=None, F2t:VariableLike=None, F2c:VariableLike=None, F12:VariableLike=None, F23:VariableLike=None):
        """Initialize a transverse material object.

        Parameters
        ----------
        name : str, optional
            The name of the material. Defaults to None.
        density : VariableLike, optional
            The density of the material. Defaults to None.
        EA : VariableLike, optional
            Young's modulus in the axial direction. Defaults to None.
        ET : VariableLike, optional
            Young's modulus in the transverse direction. Defaults to None.
        vA : VariableLike, optional
            Poisson's ratio in the axial direction. Defaults to None.
        vT : VariableLike, optional
            Poisson's ratio in the transverse direction. Defaults to None.
        GA : VariableLike, optional
            Shear modulus in the axial direction. Defaults to None.
        F1t : VariableLike, optional
            Tensile strength in the 1 direction. Defaults to None.
        F1c : VariableLike, optional
            Compressive strength in the 1 direction. Defaults to None.
        F2t : VariableLike, optional
            Tensile strength in the 2 direction. Defaults to None.
        F2c : VariableLike, optional
            Compressive strength in the 2 direction. Defaults to None.
        F12 : VariableLike, optional
            Shear strength in the 1-2 plane. Defaults to None.
        F23 : VariableLike, optional
            Shear strength in the 2-3 plane. Defaults to None.
        """
        super().__init__(name=name, density=density)

                 



    def set_compliance(self, EA:float, ET:float, vA:float, GA:float, vT:float=None, GT:float=None):
        """Set the compliance matrix for the material.

        This method calculates and sets the compliance matrix based on the given material properties.

        Parameters
        ----------
        EA : float
            Young's modulus in the axial direction.
        ET : float
            Young's modulus in the transverse direction.
        vA : float
            Poisson's ratio in the axial direction.
        GA : float
            Shear modulus in the axial direction.
        vT : float, optional
            Poisson's ratio in the transverse direction. Default is None.
        GT : float, optional
            Shear modulus in the transverse direction. Default is None.

        Raises
        ------
        Exception
            If the material properties are not sufficient to define the compliance matrix.
        """
        if vT is not None and GT is None:
            GT = ET / (2 * (1 + vT))  # = G23
        elif GT is not None and vT is None:
            vT = ET / (2 * GT) - 1
        else:
            raise Exception('Material is underdefined')

        self.compliance = np.array(
            [[1 / ET, -vT / ET, -vA / EA, 0, 0, 0],
             [-vT / ET, 1 / ET, -vA / EA, 0, 0, 0],
             [-vA / EA, -vA / EA, 1 / EA, 0, 0, 0],
             [0, 0, 0, 1 / GA, 0, 0],
             [0, 0, 0, 0, 1 / GA, 0],
             [0, 0, 0, 0, 0, 1 / GT]]
        )

    def from_compliance(self):
        """Calculate material properties from compliance matrix.

        Returns
        -------
        tuple
            A tuple containing the following material properties:
            - EA: Young's modulus in the axial direction
            - ET: Young's modulus in the transverse direction
            - vA: Poisson's ratio in the axial direction
            - vT: Poisson's ratio in the transverse direction
            - GA: Shear modulus
        """
        ET = 1/self.compliance[0,0]
        EA = 1/self.compliance[5,5]
        vT = -self.compliance[1,0]*ET
        vA = -self.compliance[2,0]*EA
        GA = 1/self.compliance[3,3]        
        return EA, ET, vA, vT, GA

    def set_strength(self, F1t, F1c, F2t, F2c, F12, F23):
        self.strength = np.array(
            [[F1t, F2t, F2t],
            [F1c, F2c, F2c],
            [F12, F12, F23]]
            )
        

def import_material(fname:str) -> Material:
    """Import material from an XML file.

    Parameters
    ----------
    fname : str
        The name of the file to import from.

    Returns
    -------
    Material
        The material object.
    """


    tree = ET.parse(fname)
    root = tree.getroot()
    name = root.attrib['name']

    mat_type = root.attrib['type']
    if mat_type == 'IsotropicMaterial':
        material = IsotropicMaterial()
    elif mat_type == 'TransverseMaterial':
        material = TransverseMaterial()
    else:
        material = Material()

    material.name = name
    
    if root.find('density') is not None: 
        material.density = float(root.find('density').text)
    
    if root.find('compliance') is not None:
        material.compliance = np.array(
            [[float(x) for x in i.text.split()] 
            for i in root.find('compliance')]
            )
    
    if root.find('strength') is not None:
        material.strength = np.array(
            [[float(x) for x in i.text.split()] 
            for i in root.find('strength')]
            )
    
    return material