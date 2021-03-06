# Modifed by Keyang Xu
#Weighted K-Means - subspace clustering with cluster dependant weight
#
#data
#    numpy.array data set. It should be standardized (for best results). Format: entities x features
#k
#    Number of clusters.
#beta
#    The weight exponent, as per original paper
#init_centroids
#   Initial centroids. Format: centroids x features
#init_weights
#   Initial weights. Format: number of clusters x features
#dist
#   Distance in use.
#replicates
#    Number of times you want to run WK-Means. The method will return the clustering with smallest
#    WK-Means output criterion (weighted sum of distances between entities and respective centroids)
#p
#   The distance exponent of the Minkowski and Minkowski_pthPower distances. Not used if you select a different distance
#max_ite
#   The maximum number of iterations allowed in K-Means
########################################################################################################################
#
# More info:
#
#Huang, J.Z., Ng, M.K., Rong, H., Li, Z.: Automated variable weighting in k-means type clustering. Pattern Analysis and
## Machine Intelligence, IEEE Transactions on 27(5), 657-668 (2005)
#
#Huang, J.Z., Xu, J., Ng, M., Ye, Y.: Weighting method for feature selection in k-#means. Computational Methods of
#Feature Selection, Chapman & Hall/CRC pp. 193-209 (2008)


import random as rd
import numpy as np
import collections

class WKMeans(object):

    def __init__(self):
        self.name = "wkmeans"

    def get_distance(self, data , centroid, distance,weight=None):
        if distance == 'Euclidean':
            if weight is None:
                #print str(data) + "\t" + str(centroid) + "\t" + str(np.sum((data - centroid)**2))
                return np.sum((data - centroid)**2)

            else: 
                #s = np.dot(((data - centroid)**2),np.ones(weight.reshape(-1,1).shape))
                s = np.dot(((data - centroid)**2), weight.reshape((-1,1)))
                return s[:,0]
        elif distance == "Cosine":
            similarity =  np.dot(data, centroid.T)
            row = similarity.shape[0]
            return np.ones(row) - similarity

    def get_center(self, data, distance):
        return data.sum(axis=0)/float((data.shape[0]))

    def dist_from_centers(self,indexes):
        t = len(indexes)
        #assign entities to cluster
        self.dist[:, t-1] = self.get_distance(self.data, self.data[indexes[t-1],:], self.distance)
        u = self.dist.argmin(axis=1)
        return self.dist[np.arange(self.dist.shape[0]), u]

    def choose_next_center(self,D):
        self.probs = D/D.sum()
        self.cumprobs = self.probs.cumsum()
        r = rd.random()
        index = np.where(self.cumprobs >= r)[0][0]
        return index

    def get_kpp_centroids(self,k):
        self.dist = np.ones([self.n_entities, k])
        indexes = [rd.randint(0,self.n_entities-1)]
        while len(indexes) < k:
            D = self.dist_from_centers(indexes)
            next_index = self.choose_next_center(D)
            indexes.append(next_index)
        return indexes


    def _get_centroid_based_weights(self,data, centroids, weights, k , beta, u, n_features, distance):
        global_centroid = np.mean(data, axis=0)   
        c = collections.Counter(u)
        inter_dispersion = np.zeros([k, n_features])
        intra_dispersion = np.zeros([k,n_features])

        for k_i in range(k):
            for f_i in range(n_features):
                inter_dispersion[k_i, f_i] = float(c[k_i]) * self.get_distance(centroids[k_i,f_i],global_centroid[f_i],distance)
                intra_dispersion[k_i, f_i] = self.get_distance(data[u == k_i, f_i], centroids[k_i, f_i], distance)
        
        intra_dispersion += 1.0/257 # smoothing
        inter_dispersion += 1.0/257
        delta_weights = np.zeros([k, n_features])     

        for k_i in range(k):
            for f_i in range(n_features):
                delta_weights[k_i, f_i] = inter_dispersion[k_i,f_i]/intra_dispersion[k_i,f_i]
        # normalize
        row_sums = delta_weights.sum(axis=1)
        delta_weights = delta_weights/row_sums[:, np.newaxis]
        #weights = (weights + delta_weights)/2.0
        #print weights
        return delta_weights

    def _get_dispersion_based_weights(self, data, centroids, k, beta, u, n_features, distance, dispersion_update='mean'):
        dispersion = np.zeros([k, n_features])
        for k_i in range(k):
            for f_i in range(n_features):
                dispersion[k_i, f_i] = self.get_distance(data[u == k_i, f_i], centroids[k_i, f_i], distance)
        '''
        print "----before---"
        print dispersion
        '''
        # smoothing using the global mean..
        if dispersion_update == 'mean':
            dispersion += dispersion.mean()
            #dispersion += 0.0001
        else:
            dispersion += dispersion_update
        #calculate the actual weight
        '''
        print centroids
        print dispersion
        print u
        '''
        weights = np.zeros([k, n_features])
        if beta != 1:
            exp = 1/(beta - 1)
            for k_i in range(k):
                for f_i in range(n_features):
                    weights[k_i, f_i] = 1/((dispersion[k_i, f_i].repeat(n_features)/dispersion[k_i, :])**exp).sum()
        else:
            for k_i in range(k):
                weights[k_i, dispersion[k_i, :].argmin()] = 1
        #print weights
        return weights

    def __wk_means(self, data, k, beta, init_centroids="kmeans++", weights=None, weight_method=None, max_ite=100, distance='Euclidean'):
        #runs WK-Means (or MWK-Means) once
        #returns -1, -1, -1, -1, -1 if there is an empty cluster
        n_entities, n_features = data.shape[0],data.shape[1]
        self.n_entities,self.n_features,self.data,self.distance = n_entities, n_features, data, distance
        if init_centroids == "random":
            centroids = data[rd.sample(range(n_entities), k), :]
        elif init_centroids == "kmeans++":
            indexes = self.get_kpp_centroids(k)
            centroids = data[indexes,:]    
        if weights is None:
            if distance == 'Euclidean':
                #as per WK-Means paper
                weights = np.random.rand(k, n_features)
                weights = weights/weights.sum(axis=1).reshape([k, 1]) # normalize each line

        previous_u = np.array([])
        previous_dist_sum = 0.0
        ite = 1
        while ite <= max_ite:
            #print "========= " + str(ite) + "=========="
            dist_tmp = np.zeros([n_entities, k])
            #assign entities to cluster
            for k_i in range(k):
                if weight_method == "centroid":
                    dist_tmp[:, k_i] = self.get_distance(data, centroids[k_i, :], distance, weights[k_i, :])
                else:
                    dist_tmp[:, k_i] = self.get_distance(data, centroids[k_i, :], distance, weights[k_i, :]**beta) # ** means exponent
            u = dist_tmp.argmin(axis=1) # min distance with k centroids, return the index not the value
            #put the sum of distances to centroids in dist_tmp 
            dist_vector = dist_tmp[np.arange(dist_tmp.shape[0]),u]
            dist_sum = np.sum(dist_tmp[np.arange(dist_tmp.shape[0]), u])
            
            #stop if there are no changes in the partitions
            #if np.array_equal(u, previous_u):
            #if abs(dist_sum - previous_dist_sum)<0.000001 or 
            if np.array_equal(u, previous_u):
                if weight_method is None:
                    weights = self._get_dispersion_based_weights(data, centroids, k, beta, u, n_features, distance)
                elif weight_method == "centroid":
                    print "centroids converge"
                    weights = self._get_centroid_based_weights(data,centroids, weights, k, beta, u, n_features, distance)
                return u, centroids, weights, ite, dist_sum
            #update centroids
            for k_i in range(k):
                entities_in_k = u == k_i # entities == k_i and u == k_i
                #Check if cluster k_i has lost all its entities
                if sum(entities_in_k) == 0:
                    index = dist_vector.argmax(axis=0)
                    u[index] = k_i
                    dist_vector[index] = 0.0
                    entities_in_k = index
                centroids[k_i, :] = self.get_center(data[entities_in_k, :], distance)
            #update weights
            if weight_method is None:
                weights = self._get_dispersion_based_weights(data, centroids, k, beta, u, n_features, distance)
            elif weight_method == "centroid":
                #print "centroids!"
                weights = self._get_centroid_based_weights(data,centroids, weights, k, beta, u, n_features, distance)
            previous_u = u[:]
            previous_dis_sum = dist_sum
            ite += 1
        return np.array([-1]), np.array([-1]), np.array([-1]), np.array([-1]), np.array([-1])

    def  wk_means(self, data, k, beta=2, init_centroids="kmeans++", init_weights=None, weight_method=None, distance='Euclidean', replicates=50, max_ite=100):
        #Weighted K-Means
        final_dist = float("inf")
        avg_iteration = []
        for replication_i in range(replicates):
            #print replication_i
            #loops up to max_ite to try to get a successful clustering for this replication
            [u, centroids, weights, ite, dist_tmp] = self.__wk_means(data, k, beta, init_centroids, init_weights, weight_method, max_ite, distance)
            if u[0] == -1:
                #raise Exception('Cannot generate a single successful clustering')
                print ("this run cannot converge to stable status")
                continue
            #given a successful clustering, check if its the best
            if dist_tmp < final_dist:
                final_u = u[:]
                final_centroids = centroids[:]
                final_dist = dist_tmp
                final_weights = weights
            print str(replication_i) + " has " + str(ite) + " iterations."
            avg_iteration.append(ite)
        final_ite = sum(avg_iteration)/float(len(avg_iteration))
        self.final_u, self.final_centroids, self.final_weights,self.beta, self.k = final_u, final_centroids, final_weights, beta, k
        return final_u, final_centroids, final_weights, final_ite, final_dist

    def wk_means_classify(self, data, distance='Euclidean'):
        k, beta, weights, centroids = self.k, self.beta, self.final_weights, self.final_centroids
        n_entities, n_features = data.shape[0],data.shape[1]
        dist_tmp = np.zeros([n_entities, k])
        for k_i in range(k):
            dist_tmp[:, k_i] = self.get_distance(data, centroids[k_i, :], distance, weights[k_i, :]**beta) # ** means exponent
        u = dist_tmp.argmin(axis=1)
        return u

if __name__=='__main__':
    t = WKMeans()
    data = np.array([[1.0,0.0],[2.0,0.0],[3.0,0.0],[0.0,3.0],[0.0,4.0],[0.0,5]])
    final_u, final_centroids, weights, final_ite, final_dist = t.wk_means(data,2,2, replicates=1,weight_method="centroid")
    print final_u
    print collections.Counter(final_u)
    print weights
    print final_centroids
    test_data = np.array([[0.0,4],[2.0,0.0]])
    t.wk_means_classify(test_data)
