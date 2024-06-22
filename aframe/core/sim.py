import numpy as np
import matplotlib.pyplot as plt
import aframe as af
from scipy.integrate import solve_ivp
import csdl_alpha as csdl
import imageio


class Simulation:

    def __init__(self, solution, start, stop, nt):

        self.M = solution.M.value
        self.K = solution.K.value
        self.F = solution.F.value
        self.u0 = solution.u0.value
        self.nu = len(self.u0)
        self.start = start
        self.stop = stop
        self.nt = nt
        self.index = solution.index
        self.node_dictionary = solution.node_dictionary

    def _ode(self, t, y):
        u = y[0:self.nu]
        u_dot = y[self.nu:-1]
        u_ddot = np.linalg.solve(self.M, self.F*np.cos(1000*t) - self.K @ u)
        # u_ddot = np.linalg.solve(self.M, self.F - self.K @ u)
        return np.concatenate((u_dot, u_ddot))

    def solve(self):
        # start and end time
        t_span = (self.start, self.stop)
        # times at which to store the computed solution
        t_eval = np.linspace(t_span[0], t_span[1], self.nt)

        # solve the ode
        sol = solve_ivp(self._ode, t_span, self.u0, t_eval=t_eval, method='Radau') 
        # 'LSODA' works well also

        t = sol.t
        u = sol.y[0:self.nu]

        return t, u
    
    def parse_u(self, u, beam):

        def_mesh = np.zeros((beam.num_nodes, 3, self.nt))

        for i in range(self.nt):
            for j in range(beam.num_nodes):
                node_index = self.index[self.node_dictionary[beam.name][j]] * 6
                def_mesh[j, :, i] = beam.mesh.value[j, :] + u[node_index:node_index + 3, i]
        
        return def_mesh
    
    def create_frames(self, mesh_list, xlim, ylim, figsize, ax1=1, ax2=2):

        # fig = plt.figure(figsize=figsize)
        
        for i in range(self.nt):

            fig = plt.figure(figsize=figsize)

            for j in range(len(mesh_list)):
                mesh = mesh_list[j]

                # fig = plt.figure(figsize=figsize)

                plt.plot(mesh[:, ax1, i], mesh[:, ax2, i], c='black', linewidth=3, zorder=2, label='_nolegend_')
                plt.scatter(mesh[:, ax1, i], mesh[:, ax2, i], marker='o', s=100, c='green', edgecolor='black', zorder=3, alpha=1, label='_nolegend_')


            plt.xlim(xlim)
            plt.ylim(ylim)

            # plt.axhline(0, color='black', linewidth=1, zorder=1)
            # x = np.linspace(xlim[0], xlim[1], 10)
            # plt.fill_between(x, -10, 0, color='skyblue', alpha=0.4, hatch='/')

            # plt.axvline(0, color='black', linewidth=1, zorder=1)
            # y = np.linspace(ylim[0], ylim[1], 10)
            # plt.fill_betweenx(y, x1=-1, x2=0, color='black', alpha=0.4, hatch='/')

            plt.xlabel('x (m)')
            plt.ylabel('y (m)')

            plt.savefig(f'img/img_{i}.png', transparent=True, dpi=100, facecolor='white', bbox_inches="tight")

            plt.close()
        
            # plt.title(title, fontsize=fontsize)
            # plt.xticks(fontsize=fontsize - 2)
            # plt.yticks(fontsize=fontsize - 2)

    def gif(self, filename, fps):

        frames = []
        for i in range(self.nt):
            image = imageio.v2.imread(f'img/img_{i}.png')
            frames.append(image)

        # to save the gif with imageio
        imageio.mimsave(filename, frames, fps=fps)