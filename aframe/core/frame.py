import numpy as np
import aframe as af
# import scipy.sparse as sp
# import scipy.sparse.linalg as spla
import csdl_alpha as csdl

class Frame:
    def __init__(self):

        self.beams = []
        self.joints = []
        self.acc = None
        self.displacement = {}
        self.cg = None
        self.mass = None
        self.residual = None
        self.dim = None
        self.num = None


    def add_beam(self, beam:'af.Beam'):

        self.beams.append(beam)


    def add_joint(self, members:list, nodes:list):
        
        self.joints.append({'members': members, 'nodes': nodes})


    def add_acc(self, acc:np.array):

        if acc.shape != (6,):
            raise ValueError("acc must have shape 6")

        if self.acc is None:
            self.acc = acc
        else:
            raise ValueError("acc is not None")
        
    
    def _utils(self):

        idx = 0
        for beam in self.beams:
            beam.map.extend(range(idx, idx + beam.num_nodes))
            idx += beam.num_nodes

        # re-assign joint nodes
        for joint in self.joints:
            members = joint['members']
            nodes = joint['nodes']
            index = members[0].map[nodes[0]]

            for i, member in enumerate(members):
                if i != 0:
                    member.map[nodes[i]] = index

        # nodes = set()
        # for beam in self.beams:
        #     for i in range(beam.num_nodes):
        #         nodes.add(beam.map[i])
        # a faster version of the above code
        nodes = {node for beam in self.beams for node in beam.map[:beam.num_nodes]}
        
        # the global dimension is the number of unique nodes times
        # the degrees of freedom per node
        num = len(nodes)
        dim = num * 6

        helper = {node: i for i, node in enumerate(nodes)}

        for beam in self.beams:
            map = beam.map
            
            for i in range(beam.num_nodes):
                map[i] = helper[map[i]] * 6

        return dim, num
    

    def _mass_properties(self):

        # mass properties
        mass, rmvec = 0, 0
        for beam in self.beams:
            beam_mass, beam_rmvec = beam._mass()
            mass += beam_mass
            rmvec += beam_rmvec

        self.cg = rmvec / mass
        self.mass = mass

        return None
    

    def compute_stress(self):

        # calculate the elemental loads and stresses
        stress = {}
        for beam in self.beams:
            # elemental loads
            element_loads = beam._recover_loads(self.U)
            # element_loads = csdl.vstack(element_loads)
            # perform a stress recovery
            beam_stress = beam.cs.stress(element_loads)

            stress[beam.name] = beam_stress
        return stress
    

    def _displacements(self, U):

        # find the displacements
        for beam in self.beams:
            self.displacement[beam.name] = csdl.Variable(value=np.zeros((beam.num_nodes, 3)))
            map = beam.map

            map_u_to_d_x, map_u_to_d_y, map_u_to_d_z = [], [], []
            for i in range(beam.num_nodes):
                idx = map[i]
                map_u_to_d_x.append(idx)
                map_u_to_d_y.append(idx + 1)
                map_u_to_d_z.append(idx + 2)
                # extract the (x, y, z) nodal displacement
                # displacement[beam.name] = displacement[beam.name].set(csdl.slice[i, :], U[idx:idx+3])

            reshaped_U = csdl.transpose(csdl.vstack([U[map_u_to_d_x], U[map_u_to_d_y], U[map_u_to_d_z]]))
            self.displacement[beam.name] = self.displacement[beam.name].set(csdl.slice[:, :], reshaped_U)

        return None
    

    def _global_matrices(self):

        # create the global stiffness matrix
        # and the global mass matrix
        K = csdl.Variable(value=np.zeros((self.dim, self.dim)))
        M = csdl.Variable(value=np.zeros((self.dim, self.dim)))

        for beam in self.beams:
            transformed_stiffness_matrices = beam.transformed_stiffness
            transformed_mass_matrices = beam.transformed_mass
            # add the elemental stiffness/mass matrices to their locations in the 
            # global stiffness/mass matrix
            map = beam.map

            for i in range(beam.num_elements):
            # for i, idxa, idxb in csdl.frange(vals = (list(range(beam.num_elements)), map[:-1], map[1:])):
                stiffness = transformed_stiffness_matrices[i]
                mass_matrix = transformed_mass_matrices[i]
                idxa, idxb = map[i], map[i+1]

                K = K.set(csdl.slice[idxa:idxa+6, idxa:idxa+6], K[idxa:idxa+6, idxa:idxa+6] + stiffness[:6, :6])
                K = K.set(csdl.slice[idxa:idxa+6, idxb:idxb+6], K[idxa:idxa+6, idxb:idxb+6] + stiffness[:6, 6:])
                K = K.set(csdl.slice[idxb:idxb+6, idxa:idxa+6], K[idxb:idxb+6, idxa:idxa+6] + stiffness[6:, :6])
                K = K.set(csdl.slice[idxb:idxb+6, idxb:idxb+6], K[idxb:idxb+6, idxb:idxb+6] + stiffness[6:, 6:])

                M = M.set(csdl.slice[idxa:idxa+6, idxa:idxa+6], M[idxa:idxa+6, idxa:idxa+6] + mass_matrix[:6, :6])
                M = M.set(csdl.slice[idxa:idxa+6, idxb:idxb+6], M[idxa:idxa+6, idxb:idxb+6] + mass_matrix[:6, 6:])
                M = M.set(csdl.slice[idxb:idxb+6, idxa:idxa+6], M[idxb:idxb+6, idxa:idxa+6] + mass_matrix[6:, :6])
                M = M.set(csdl.slice[idxb:idxb+6, idxb:idxb+6], M[idxb:idxb+6, idxb:idxb+6] + mass_matrix[6:, 6:])

        return K, M
    

    def _global_loads(self, M):

        # assemble the global loads vector
        F = csdl.Variable(value=np.zeros((self.dim)))
        for beam in self.beams:
            loads = beam.loads # shape: (n, 6)
            map = beam.map # shape: (n,)

            if loads is not None:

                for i in range(beam.num_nodes):
                    idx = map[i]
                    F = F.set(csdl.slice[idx:idx+6], F[idx:idx+6] + loads[i, :])

        
        # add any inertial loads
        acc = self.acc
        if acc is not None:
            # expanded_acc = np.tile(self.acc, num)
            expanded_acc = csdl.expand(acc, (self.num, 6), action='i->ji').flatten()
            primary_inertial_loads = csdl.matvec(M, expanded_acc)
            F += primary_inertial_loads

            # added inertial masses are resolved as loads
            for beam in self.beams:
                # if the beam has extra inertial mass
                if beam.extra_inertial_mass is not None:
                    extra_mass = beam.extra_inertial_mass
                    extra_inertial_loads = csdl.outer(extra_mass, acc)
                    map = beam.map

                    for i in range(beam.num_nodes):
                        idx = map[i]
                        F = F.set(csdl.slice[idx:idx+6], F[idx:idx+6] + extra_inertial_loads[i, :])

        return F
    

    def _boundary_conditions(self, K, M, F):

        # apply boundary conditions
        indices = []
        for beam in self.beams:
            map = beam.map

            for node in beam.boundary_conditions:
                idx = map[node]
                for i in range(6):
                    # if dof[i] == 1:
                    indices.append(idx + i)

        # zero the row/column then put a 1 in the diagonal
        K = K.set(csdl.slice[indices, :], 0)
        K = K.set(csdl.slice[:, indices], 0)
        K = K.set(csdl.slice[indices, indices], 1)
        # zero the row/column then put a 1 in the diagonal
        M = M.set(csdl.slice[indices, :], 0)
        M = M.set(csdl.slice[:, indices], 0)
        M = M.set(csdl.slice[indices, indices], 1)
        # zero the corresponding load index as well
        F = F.set(csdl.slice[indices], 0)

        return K, M, F
    

    def dynamic_residual(self):
        pass
        # return residual
    

    def solve(self, do_residual=False, U=None, U_dotdot=None):

        # helper functions
        dim, num = self._utils()
        self.dim = dim
        self.num = num

        # calculate the mass properties
        self._mass_properties()
        
        # create the global stiffness/mass matrices
        K, M = self._global_matrices()

        # assemble the global loads vector
        F = self._global_loads(M)

        # apply boundary conditions
        K, M, F = self._boundary_conditions(K, M, F)



        # solve the system of equations
        if do_residual:
            R = csdl.matvec(K, U) + csdl.matvec(M, U_dotdot) - F
            self.residual = R

            # find the displacements
            self._displacements(U)

        else:
            U = csdl.solve_linear(K, F)
            self.residual = csdl.matvec(K, U) - F

            # find the displacements
            self._displacements(U)


        return None